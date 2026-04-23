# Toroto — Plataforma geoespacial territorial

Monorepo de una plataforma geoespacial para operar intervenciones territoriales con API, mapas, autenticación y consultas asistidas por IA.

- `apps/api` — API FastAPI + PostGIS con autenticación JWT
- `apps/web` — frontend React con MapLibre GL y consultas en lenguaje natural
- `deploy/vps` — configuración Docker + Nginx para VPS
- `docs` — arquitectura, trade-offs y capa de IA

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI 0.116, Python 3.12 |
| Base de datos | PostgreSQL 16 + PostGIS, GeoAlchemy2 |
| Migraciones | Alembic (idempotente) |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| Modelo IA | GPT-OSS-20B vía Fyra, fallback heurístico |
| Frontend | React 19, Vite, MapLibre GL |
| Deploy | Docker Compose + Nginx (VPS), Cloudflare Pages (web) |
| CI/CD | GitHub Actions |

## Consultas disponibles

- `POST /auth/login` — autenticación, devuelve JWT Bearer
- `POST /geospatial/nearest` — intervención más cercana a una coordenada
- `GET /geospatial/nearest-to-place?place=guanajuato` — más cercana a un lugar de referencia
- `GET /geospatial/farthest-from-place?place=cancun` — más lejana desde un lugar
- `POST /geospatial/within-radius` — intervenciones dentro de un radio en km
- `POST /geospatial/within-area` — intervenciones dentro de un polígono
- `GET /geospatial/count-by-region` — agregados por región operativa
- `POST /geospatial/ask` — consulta en lenguaje natural con intención estructurada

Todos los endpoints `/geospatial/*` requieren `Authorization: Bearer <token>`.

## Arquitectura de la capa de IA

El flujo de `/ask` nunca genera SQL. El modelo extrae una `GeoIntent` (JSON estructurado), y la API ejecuta la consulta PostGIS determinística correspondiente:

```
pregunta → LLM (GeoIntent) → query PostGIS → resultado
                ↓ falla
           heurístico regex → GeoIntent
```

Esto hace la capa de IA auditable, testeable y predecible.

## Deploy

- Frontend: `test-toroto.lobami.lat` (Cloudflare Pages)
- API: `api-test-toroto.lobami.lat` (VPS + Nginx)

### Variables de entorno requeridas (VPS)

```
DATABASE_URL=postgresql+psycopg://user:pass@db:5432/toroto
ALLOWED_ORIGINS=https://test-toroto.lobami.lat
FYRA_API_KEY=...
FYRA_BASE_URL=https://api.fyra.im/v1
FYRA_MODEL=gpt-oss-20b
JWT_SECRET=<secreto aleatorio largo>
```

Configurar `JWT_SECRET` como GitHub Secret (`JWT_SECRET`) antes del primer deploy.

### Primer deploy con datos

```bash
# Deploy normal (solo migraciones + rebuild)
deploy/vps/remote-deploy.sh

# Carga inicial de datos (solo primera vez o reset)
deploy/vps/remote-seed.sh
```

Las migraciones corren automáticamente al iniciar el contenedor. El usuario `toroto` se crea en el primer arranque si no existe.

### Acceso demo

| Campo | Valor |
|---|---|
| Usuario | `toroto` |
| Contraseña | `toroto573` |

## Datos

~1000 intervenciones territoriales sintéticas distribuidas en todas las regiones de México, más 51 lugares de referencia (28 estados + 23 ciudades principales).
