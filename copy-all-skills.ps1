$projectRoot = "c:\Users\barah\Desktop\Pranely"
$skillsDest = Join-Path $projectRoot ".agents\skills"

$baseSkills = @(
    "code-review-security",
    "create-auth-skill",
    "deployment-pipeline",
    "fastapi-patterns",
    "fastapi-pro",
    "find-skills",
    "frontend-design",
    "next-best-practices",
    "nodejs-backend-patterns",
    "playwright-best-practices",
    "shadcn",
    "systematic-debugging"
)

foreach ($skill in $baseSkills) {
    $src = Join-Path $projectRoot $skill
    $dst = Join-Path $skillsDest $skill
    if (Test-Path $src) {
        if (-not (Test-Path $dst)) {
            New-Item -ItemType Directory -Path $dst -Force | Out-Null
        }
        Copy-Item -Path "$src\*" -Destination $dst -Recurse -Force
        Write-Host "Copied: $skill"
    }
}

Write-Host "`nTotal skills in .agents/skills/:"
Get-ChildItem -Path $skillsDest -Directory | Measure-Object | Select-Object -ExpandProperty Count
Get-ChildItem -Path $skillsDest -Directory | Select-Object Name
