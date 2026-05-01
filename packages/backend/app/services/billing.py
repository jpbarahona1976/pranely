"""Billing service layer - centralizado para sync suscripción/cuotas/lock."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BillingPlan,
    BillingPlanCode,
    Organization,
    Subscription,
    SubscriptionStatus,
    UsageCycle,
)


logger = logging.getLogger(__name__)


class BillingService:
    """
    Service centralizado para operaciones de billing.
    
    Principios:
    - Toda query filtra por org_id (multi-tenant)
    - Idempotencia en operaciones sensibles
    - Logging con contexto para trazabilidad
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_organization(self, org_id: int) -> Optional[Organization]:
        """Obtener organización por ID."""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_plan_by_code(self, code: BillingPlanCode) -> Optional[BillingPlan]:
        """Obtener plan por código."""
        result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.code == code)
        )
        return result.scalar_one_or_none()

    async def get_subscription(self, org_id: int) -> Optional[Subscription]:
        """Obtener suscripción activa de organización."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_usage_cycle(
        self, subscription: Subscription, month_year: Optional[str] = None
    ) -> UsageCycle:
        """
        Obtener o crear ciclo de uso para el mes actual.
        
        Args:
            subscription: Suscripción activa
            month_year: Periodo YYYY-MM, default mes actual
        
        Returns:
            UsageCycle para el periodo solicitado
        """
        if month_year is None:
            month_year = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Buscar ciclo existente
        result = await self.db.execute(
            select(UsageCycle).where(
                UsageCycle.subscription_id == subscription.id,
                UsageCycle.month_year == month_year,
            )
        )
        usage = result.scalar_one_or_none()
        
        if usage is None:
            # Obtener límites del plan
            plan_result = await self.db.execute(
                select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
            )
            plan = plan_result.scalar_one_or_none()
            
            # Crear nuevo ciclo
            usage = UsageCycle(
                subscription_id=subscription.id,
                month_year=month_year,
                docs_used=0,
                docs_limit=plan.doc_limit if plan else 100,
            )
            self.db.add(usage)
            await self.db.flush()
            logger.info(
                f"Created usage cycle for subscription={subscription.id}, "
                f"period={month_year}, limit={plan.doc_limit if plan else 100}"
            )
        
        return usage

    async def check_quota_available(self, org_id: int) -> tuple[bool, str]:
        """
        Verificar si la organización tiene cuota disponible.
        
        Returns:
            (disponible: bool, mensaje: str)
            - (True, "OK") si hay cuota
            - (False, "Suscripción inactiva") si no hay suscripción activa
            - (False, "Cuota agotada") si docs_used >= docs_limit
        """
        subscription = await self.get_subscription(org_id)
        
        if subscription is None:
            return True, "No subscription - using free tier"
        
        if subscription.status != SubscriptionStatus.ACTIVE:
            return False, f"Subscription status: {subscription.status.value}"
        
        plan_result = await self.db.execute(
            select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        
        # Plan sin límite (0 = unlimited)
        if plan and plan.doc_limit == 0:
            return True, "Unlimited plan"
        
        usage = await self.get_or_create_usage_cycle(subscription)
        
        # Verificar si está bloqueado
        if usage.is_locked:
            return False, "Billing cycle locked"
        
        # Verificar límite
        if plan and usage.docs_used >= plan.doc_limit:
            return False, f"Quota exceeded: {usage.docs_used}/{plan.doc_limit}"
        
        return True, f"OK: {usage.docs_used}/{plan.doc_limit if plan else '?'}"

    async def increment_usage(self, org_id: int, count: int = 1) -> bool:
        """
        Incrementar contador de documentos usados.
        
        Args:
            org_id: ID de organización
            count: Cantidad a incrementar (default 1)
        
        Returns:
            True si se incrementò correctamente
            False si no hay cuota disponible
        """
        available, message = await self.check_quota_available(org_id)
        
        if not available:
            logger.warning(f"Quota not available for org={org_id}: {message}")
            return False
        
        subscription = await self.get_subscription(org_id)
        if subscription is None:
            # Free tier sin suscripción - no trackear uso
            return True
        
        usage = await self.get_or_create_usage_cycle(subscription)
        usage.docs_used += count
        await self.db.flush()
        
        logger.info(
            f"Usage incremented: org={org_id}, added={count}, "
            f"total={usage.docs_used}/{usage.docs_limit}"
        )
        return True

    async def sync_subscription_from_stripe(
        self,
        stripe_customer_id: str,
        stripe_sub_id: Optional[str],
        plan_code: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> Optional[Subscription]:
        """
        Sincronizar suscripción desde datos de Stripe webhook.
        
        Args:
            stripe_customer_id: ID de cliente Stripe
            stripe_sub_id: ID de suscripción Stripe
            plan_code: Código del plan (free/pro/enterprise)
            period_start: Inicio del periodo de facturación
            period_end: Fin del periodo de facturación
            status: Estado de Stripe (active/trialing/past_due/canceled)
        
        Returns:
            Subscription actualizada o creada
        """
        # Buscar organización por stripe_customer_id
        result = await self.db.execute(
            select(Organization).where(
                Organization.stripe_customer_id == stripe_customer_id
            )
        )
        org = result.scalar_one_or_none()
        
        if org is None:
            logger.error(f"Organization not found for stripe_customer_id={stripe_customer_id}")
            return None
        
        # Obtener plan
        try:
            code = BillingPlanCode(plan_code)
        except ValueError:
            code = BillingPlanCode.FREE
        
        plan = await self.get_plan_by_code(code)
        if plan is None:
            logger.error(f"Plan not found: {plan_code}")
            return None
        
        # Buscar suscripción existente
        subscription = await self.get_subscription(org.id)
        
        now = datetime.now(timezone.utc)
        
        if subscription is None:
            # Crear nueva suscripción
            subscription = Subscription(
                organization_id=org.id,
                plan_id=plan.id,
                stripe_customer_id=stripe_customer_id,
                stripe_sub_id=stripe_sub_id,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                current_period_start=period_start or now,
                current_period_end=period_end,
            )
            self.db.add(subscription)
            logger.info(f"Created subscription for org={org.id}, plan={plan_code}")
        else:
            # Actualizar suscripción existente
            subscription.plan_id = plan.id
            subscription.stripe_sub_id = stripe_sub_id
            
            # Mapear estado Stripe
            status_map = {
                "active": SubscriptionStatus.ACTIVE,
                "trialing": SubscriptionStatus.ACTIVE,
                "past_due": SubscriptionStatus.PAST_DUE,
                "canceled": SubscriptionStatus.CANCELLED,
                "unpaid": SubscriptionStatus.PAST_DUE,
            }
            
            if status:
                subscription.status = status_map.get(status, subscription.status)
            
            if period_start:
                subscription.current_period_start = period_start
            if period_end:
                subscription.current_period_end = period_end
            
            logger.info(f"Updated subscription for org={org.id}, status={subscription.status.value}")
        
        await self.db.flush()
        
        # Crear/inicializar ciclo de uso para el mes actual
        await self.get_or_create_usage_cycle(subscription)
        
        return subscription

    async def cancel_subscription(self, org_id: int) -> bool:
        """
        Cancelar suscripción de organización.
        
        Args:
            org_id: ID de organización
        
        Returns:
            True si se canceló correctamente
        """
        subscription = await self.get_subscription(org_id)
        
        if subscription is None:
            logger.warning(f"No subscription found for org={org_id}")
            return False
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        
        logger.info(f"Cancelled subscription for org={org_id}")
        return True

    def get_billing_status(self, subscription: Optional[Subscription]) -> dict:
        """
        Obtener estado de billing formateado para respuesta API.
        
        Args:
            subscription: Suscripción o None
        
        Returns:
            Dict con plan_code, status, doc_limit, docs_used, is_locked
        """
        if subscription is None:
            return {
                "plan_code": "free",
                "plan_name": "Free Tier",
                "status": "active",
                "doc_limit": 100,
                "docs_used": 0,
                "is_locked": False,
            }
        
        return {
            "plan_code": "pro",  # Se actualiza desde API con plan.code real
            "status": subscription.status.value,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
        }