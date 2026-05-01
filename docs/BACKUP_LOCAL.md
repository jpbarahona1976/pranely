# Respaldo local (entorno Docker)

> **Nota:** Este es un esquema de respaldo **LOCAL** para el entorno de desarrollo. No sustituye un plan de Disaster Recovery (DR) completo. La subfase **4C** del roadmap definirá RPO/RTO, automatización y storage externo.

---

## 4.1 Pre-requisitos

- Docker y Docker Compose v2 instalados
- Contenedor `pranely-postgres` corriendo
- Variable de entorno `POSTGRES_PASSWORD` disponible
- Espacio en disco suficiente (verificar con `df -h`)

---

## 4.2 Hacer backup de PostgreSQL

**Opción 1: Ejecutar el script**
```bash
# Desde la raíz del proyecto
chmod +x ./scripts/backup_postgres.sh
./scripts/backup_postgres.sh
```

**Opción 2: Comando directo (sin script)**
```bash
# Crear directorio si no existe
mkdir -p ./backups

# Ejecutar backup con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
docker compose exec -T postgres pg_dumpall \
    --username=pranely \
    --database=pranely_dev \
    | gzip > "./backups/pranely_postgres_${TIMESTAMP}_full.dump.gz"
```

**Verificar el backup:**
```bash
ls -lh ./backups/pranely_postgres_*.dump.gz
gunzip -c ./backups/pranely_postgres_20260428_120000_full.dump.gz | head -20
```

---

## 4.3 Hacer backup de uploads (volumen Docker)

> **Nota:** Si aún no tienes un volumen `pranely_uploads` definido, este paso es opcional. Los documentos se almacenan actualmente en la base de datos o en bind mounts del backend.

**Primero, crea el volumen si no existe:**
```bash
docker volume create pranely_uploads
```

**Ejecutar el script:**
```bash
chmod +x ./scripts/backup_uploads.sh
./scripts/backup_uploads.sh
```

---

## 4.4 Restaurar PostgreSQL desde backup

> ⚠️ **Advertencia:** La restauración sobrescribe la base de datos existente. Ejecuta con precaución en producción.

**Pasos:**

1. **Detener los servicios que usan la base de datos:**
```bash
docker compose stop backend
```

2. **Identificar el archivo de backup a restaurar:**
```bash
ls -lh ./backups/pranely_postgres_*.dump.gz
```

3. **Restaurar la base de datos:**
```bash
# Descomprimir y restaurar (reemplaza el timestamp con tu archivo)
gunzip -c ./backups/pranely_postgres_20260428_120000_full.dump.gz \
    | docker compose exec -T postgres psql \
    --username=pranely \
    --database=pranely_dev
```

4. **Verificar la restauración:**
```bash
docker compose exec postgres psql \
    --username=pranely \
    --database=pranely_dev \
    -c "SELECT COUNT(*) FROM users;"
```

5. **Reiniciar servicios:**
```bash
docker compose start backend
```

**Restauración completa del cluster (roles y settings):**
```bash
# Para restaurar el cluster completo incluyendo roles
gunzip -c ./backups/pranely_postgres_TIMESTAMP_full.dump.gz \
    | docker compose exec -T postgres psql \
    --username=pranely \
    --postgres=pranely
```

---

## 4.5 Restaurar volumen de uploads

> ⚠️ **Advertencia:** La restauración sobrescribe el contenido actual del volumen.

**Pasos:**

1. **Detener servicios:**
```bash
docker compose stop backend
```

2. **Identificar el archivo de backup:**
```bash
ls -lh ./backups/pranely_uploads_*.tar.gz
```

3. **Restaurar el volumen:**
```bash
# Opción A: Restaurar a un volumen nuevo (más seguro)
docker volume create pranely_uploads_restore
docker run --rm \
    -v pranely_uploads_restore:/data \
    -v "$(pwd)/backups:/backup:ro" \
    alpine:latest \
    tar -xzf "/backup/pranely_uploads_20260428_120000.tar.gz" -C /data

# Luego reemplazar el volumen
docker compose down
docker volume rm pranely_uploads
docker volume rename pranely_uploads_restore pranely_uploads
docker compose up -d

# Opción B: Restaurar directamente (sobrescribe datos actuales)
docker run --rm \
    -v pranely_uploads:/data \
    -v "$(pwd)/backups:/backup:ro" \
    alpine:latest \
    sh -c "rm -rf /data/* && tar -xzf /backup/pranely_uploads_TIMESTAMP.tar.gz -C /data"
```

4. **Reiniciar servicios:**
```bash
docker compose start backend
```

---

## 4.6 Script unificado de backup

Existe un script unificado que hace backup de Postgres y Redis:
```bash
chmod +x ./scripts/backup.sh
./scripts/backup.sh
```

Este script:
- Hace `pg_dump` de la base de datos (formato custom `-Fc`)
- Hace backup de Redis (dump RDB)
- Organiza backups por fecha (`backups/YYYY/MM/DD/`)

---

## 4.7 Checklist post-restauración

- [ ] Verificar que los servicios inician correctamente (`docker compose ps`)
- [ ] Probar endpoints de salud (`curl http://localhost:8000/api/health`)
- [ ] Verificar que el frontend carga (`curl http://localhost:3000`)
- [ ] Confirmar que los datos de prueba están presentes

---

## 4.8 Estructura de backups

```
backups/
├── 2026/
│   └── 04/
│       └── 28/
│           ├── postgres_20260428_120000.dump.gz
│           └── redis_20260428_120000.rdb
├── logs/
│   └── backup_20260428_120000.log
└── pranely_postgres_20260428_120000_full.dump.gz  # Script nuevo
```

---

## 4.9 Variables de entorno para backups

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `POSTGRES_PASSWORD` | (requerido) | Password de Postgres |
| `BACKUP_DIR` | `./backups` | Directorio de backups |
| `PG_HOST` | `postgres` | Host de Postgres |
| `PG_PORT` | `5432` | Puerto de Postgres |
| `PG_USER` | `pranely` | Usuario de Postgres |
| `PG_DB` | `pranely_dev` | Base de datos |
| `UPLOADS_VOLUME` | `pranely_uploads` | Volumen de uploads |

---

## 4.10 Notas de implementación (2026-04-28)

### Estado actual de volúmenes
- **Postgres**: Volumen `pranely-postgres-data` - Backup OK ✅
- **Redis**: Volumen `pranely-redis-data` - No backupeado en este script
- **Uploads**: No existe volumen `pranely_uploads` - Los archivos se almacenan en bind mount o BD

### Diferencia entre pg_dump y pg_dumpall
| Comando | Ámbito | Contenido |
|---------|--------|-----------|
| `pg_dump` | Una base de datos | Data + schema de la BD especificada |
| `pg_dumpall` | Cluster completo | Data + schema + **roles + tablespaces + settings** |

### Comandos usados en ejecución real (Windows)
```bash
# Backup Postgres (funciona en Windows sin gzip)
docker compose exec -T postgres pg_dumpall --username=pranely --database=pranely_dev -f /tmp/backup.dump
docker cp pranely-postgres:/tmp/backup.dump ./backups/pranely_postgres_TIMESTAMP_full.dump

# Restaurar Postgres
docker compose stop backend
gunzip -c backups/pranely_postgres_TIMESTAMP_full.dump.gz | docker compose exec -T postgres psql -U pranely -d pranely_dev
docker compose start backend
```

### Limitaciones actuales
1. Scripts asumen `gzip` disponible (no existe en Windows por defecto)
2. Scripts usan `grep -q "Up"` para verificar contenedor (puede fallar en algunos shells de Windows)
3. Backup de uploads requiere volumen `pranely_uploads` que aún no existe
