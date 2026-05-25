# GeoAPI — Geospatial Platform Template

Stack: FastAPI + PostGIS + React + MapLibre GL

## Features

- REST API con consultas geoespaciales (nearest neighbor, radius, polygon containment)
- Capa de lenguaje natural con LLM: extracción de intent estructurado → PostGIS
- Frontend React con mapa interactivo (MapLibre GL) y filtros operativos
- Autenticación JWT con bcrypt
- Migraciones automáticas con Alembic
- Deploy via Docker Compose + Nginx (VPS) y Cloudflare Pages (frontend/edge)
- CI/CD con GitHub Actions

## Quick start (local)

```bash
# 1. Copiar variables de entorno
cp deploy/vps/.env.example infra/.env

# 2. Levantar API + base de datos
docker compose -f infra/docker-compose.yml up -d

# 3. Cargar dataset (primera vez)
docker compose -f infra/docker-compose.yml run --rm seeder

# 4. Frontend (en otra terminal)
cd apps/web
npm install
npm run dev
```

La API queda disponible en `http://localhost:8000`.
El frontend en `http://localhost:5173`.

Credenciales por defecto: `admin` / `geoapi2025`

## Estructura

```
.
├── apps/
│   ├── api/          # FastAPI + PostGIS (Python 3.12)
│   │   ├── app/
│   │   │   ├── routers/      # endpoints REST
│   │   │   ├── services/     # lógica de negocio (auth, geospatial, nl_query)
│   │   │   ├── models/       # SQLAlchemy + GeoAlchemy2
│   │   │   └── schemas/      # Pydantic
│   │   ├── migrations/       # Alembic
│   │   └── scripts/          # seed de datos
│   ├── api-edge/     # Cloudflare Worker (proxy CORS)
│   └── web/          # React 19 + Vite + MapLibre GL
├── data/             # Dataset JSON de intervenciones
├── deploy/
│   └── vps/          # Docker Compose + Nginx + scripts de deploy
├── infra/            # Docker Compose local (dev)
└── .github/
    └── workflows/    # CI/CD pipelines
```

## Variables de entorno

Copiar `deploy/vps/.env.example` y ajustar:

```env
POSTGRES_DB=geoapi
POSTGRES_USER=geoapi
POSTGRES_PASSWORD=<contraseña segura>
DATABASE_URL=postgresql+psycopg://geoapi:<password>@postgres:5432/geoapi
ALLOWED_ORIGINS=https://<tu-dominio>,http://localhost:5173
FYRA_API_KEY=<opcional — habilita extracción de intent con LLM>
FYRA_BASE_URL=https://api.fyra.im/v1
FYRA_MODEL=gpt-oss-20b
JWT_SECRET=<secreto aleatorio largo>
ENVIRONMENT=production
```

Si `FYRA_API_KEY` no está seteado, el sistema usa un parser heurístico regex como fallback automático.

## Consultas geoespaciales disponibles

| Endpoint | Descripción |
|---|---|
| `POST /auth/login` | Autenticación, devuelve JWT Bearer |
| `POST /geospatial/nearest` | Intervención más cercana a una coordenada |
| `GET /geospatial/nearest-to-place?place=<lugar>` | Más cercana a un lugar de referencia |
| `GET /geospatial/farthest-from-place?place=<lugar>` | Más lejana desde un lugar |
| `POST /geospatial/within-radius` | Intervenciones dentro de un radio en km |
| `POST /geospatial/within-area` | Intervenciones dentro de un polígono |
| `GET /geospatial/count-by-region` | Agregados por región operativa |
| `POST /geospatial/ask` | Consulta en lenguaje natural con intent estructurado |

Todos los endpoints `/geospatial/*` requieren `Authorization: Bearer <token>`.

## Arquitectura de la capa de IA

El endpoint `/ask` nunca genera SQL directamente. El modelo extrae un `GeoIntent` (JSON estructurado), y la API ejecuta la consulta PostGIS determinística correspondiente:

```
pregunta → LLM (GeoIntent) → query PostGIS → resultado
                ↓ falla o sin API key
           heurístico regex → GeoIntent
```

Esto hace la capa de IA auditable, testeable y predecible.

## Deploy en VPS

```bash
# Primer deploy con datos
deploy/vps/remote-deploy.sh   # build + restart
deploy/vps/remote-seed.sh     # carga inicial de datos (solo primera vez)
```

Las migraciones corren automáticamente al iniciar el contenedor.

### Secretos de GitHub Actions requeridos

```
VPS_HOST, VPS_USER, VPS_PASSWORD
POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL
ALLOWED_ORIGINS, FYRA_API_KEY, FYRA_BASE_URL, FYRA_MODEL
JWT_SECRET
VITE_API_URL
CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
```
