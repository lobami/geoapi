# VPS deploy

Este directorio contiene el despliegue del backend de GeoAPI hacia la VPS compartida.

## Dominio esperado

- API: `api.yourdomain.com`

## Variables mínimas

Usa `deploy/vps/.env.example` como base para `deploy/vps/.env.production`.

## Flujo

1. GitHub Actions empaqueta el repo.
2. Sube el bundle y el archivo de entorno a la VPS.
3. `remote-deploy.sh` reconstruye contenedores.
4. El mismo script carga PostGIS y siembra el dataset en PostgreSQL.
