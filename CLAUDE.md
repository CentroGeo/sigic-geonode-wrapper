# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **sigic-geonode-wrapper**, a Django project that wraps [GeoNode](https://geonode.org/) as a library. It extends GeoNode with SIGIC-specific apps for the *Sistema Integral de Gestión e Información Científica* (CentroGeo). The stack runs entirely through Docker Compose.

## Development Commands

### Initial Setup
```bash
python3 create-envfile.py --env_type=dev --hostname=<IP or domain>
sudo sh fix_network.sh           # Creates Docker network with custom MTU (required)
sudo sh docker-build.sh          # Build + stop + up + prune (full rebuild)
```

### Day-to-day Docker
```bash
docker compose up -d             # Start services
docker compose stop              # Stop services
docker compose logs -f           # Follow logs
docker ps                        # Check container status
```

### Django Management (inside container)
```bash
docker exec -it django4sigic_geonode python manage.py migrate
docker exec -it django4sigic_geonode python manage.py shell
docker exec -it django4sigic_geonode python manage.py makemigrations sigic_scenarios
```

### Code Quality (pre-commit hooks run automatically on commit)
```bash
pip install pre-commit
pre-commit install
pre-commit run              # Run on staged files
pre-commit run --all-files  # Run on all files
pre-commit run flake8       # Run only flake8
```
Tools enforced: **flake8**, **isort**, **black**.

### Backup / Restore
```bash
docker exec -it django4sigic_geonode sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/backup.sh $BKP_FOLDER_NAME'
docker exec -it django4sigic_geonode sh -c 'SOURCE_URL=$SOURCE_URL TARGET_URL=$TARGET_URL ./sigic_geonode/br/restore.sh $BKP_FOLDER_NAME'
```

## Architecture

### Settings Chain
`src/sigic_geonode/settings.py` imports from `geonode.settings` (or `local_settings.py` if present) and extends it. All SIGIC-specific configuration happens after those base imports. Key overrides:
- **INSTALLED_APPS**: `sigic_styles` must be prepended (before `geonode.layers`) for monkeypatching; all other SIGIC apps appended.
- **MIDDLEWARE**: CSRF middleware is replaced with `SkipCSRFMiddlewareForJWT`; `KeycloakUserFromBearerInjectionMiddleware` is appended last.
- **REST_FRAMEWORK**: Adds `KeycloakJWTAuthentication` to the auth chain.

### URL Routing
`src/sigic_geonode/urls.py` mounts SIGIC paths first, then includes `geonode_urlpatterns`. SIGIC apps that register DRF ViewSets do so by importing and registering against `sigic_geonode.router.router` (a `DefaultRouter`) inside their own `urls.py`, which gets collected via `router.urls` at the end of the main urlconf.

### Authentication
Two complementary mechanisms coexist:
1. **Keycloak JWT** (`sigic_auth/keycloak.py`): `KeycloakJWTAuthentication` validates `Authorization: Bearer <token>` against Keycloak's JWKS endpoint. Used in all SIGIC DRF views.
2. **OIDC Social Auth** (`sigic_auth/account_adapters.py`): Django-allauth based login via Keycloak, configured via env vars (`SOCIALACCOUNT_OIDC_*`).

`SkipCSRFMiddlewareForJWT` exempts Bearer requests from CSRF. `KeycloakUserFromBearerInjectionMiddleware` injects `request.user` lazily from the Bearer token for non-DRF views.

### SIGIC Custom Apps (all under `src/sigic_geonode/`)

| App | Purpose |
|---|---|
| `sigic_auth` | Keycloak JWT auth, OIDC adapter, CSRF/middleware patches |
| `sigic_styles` | Must load before `geonode.layers`; applies monkeypatches |
| `sigic_datasets` | Dataset extensions on top of GeoNode's Dataset model |
| `sigic_resources` | ResourceBase extensions |
| `sigic_scenarios` | Narrative scenario editor (Scenario → Scene → SceneLayer / SceneMarker) |
| `sigic_requests` | Publication workflow (pending/on_review/published/rejected) |
| `sigic_georeference` | Tabular join/georeference operations via pandas |
| `sigic_remote_services` | File-based remote service harvester |
| `sigic_ia_media_uploads` | AI media upload endpoint |
| `sigic_account` | Account customizations |

### sigic_scenarios Data Model
Hierarchy: **Scenario** → **Scene** → (**SceneLayer** | **SceneMarker**)

- `Scenario`: owner, visibility (`is_public`), card image, layout styles JSON.
- `Scene`: ordered by `stack_order` (auto-incremented on create), map viewport, HTML text content, position (left/right).
- `SceneLayer`: references a GeoNode `Dataset` via `geonode_id`; stores WMS `name`, style, opacity, visibility, `stack_order`.
- `SceneMarker`: geographic point with popup content, Font Awesome icon, hex color.

Permission model: public scenarios are readable by anyone; write operations require the requesting user to be the `Scenario.owner` (enforced by `IsScenarioOwner` and `_check_scenario_owner` helper).

### API Endpoints (sigic_scenarios)
All registered under `api/v2/`:
- `scenarios/` — CRUD + `upload-image` action + `scenes` nested list
- `scenes/` — CRUD + `bulk-reorder` + `layers` nested list
- `scene-layers/` — CRUD + `by-scene/<id>` + `bulk-add/<scene_id>` + `bulk-delete/<scene_id>` + `bulk-reorder` + `update-style`
- `scene-markers/` — CRUD + `by-scene/<id>` + `bulk-add/<scene_id>` + `bulk-delete/<scene_id>`
- `scenarios/upload/image` — standalone image upload (5 MB limit, auto-resize to 2048px)

Pagination response shape matches GeoNode: `{links, total, page, page_size, results}`.

### Dependencies
Custom forks are pinned in `src/requirements.txt` as editable installs from GitHub:
- `sigic-geonode-mapstore-client` (branch `4.4.x.sigic`)
- `sigic-geonode-importer` (branch `1.1.x.sigic`)
- GeoNode upstream (branch `4.4.x`)

### Key Environment Variables
| Variable | Purpose |
|---|---|
| `SOCIALACCOUNT_OIDC_PROVIDER_ENABLED` | Enable/disable Keycloak OIDC login |
| `SOCIALACCOUNT_OIDC_ACCESS_TOKEN_URL` | Keycloak token endpoint |
| `SOCIALACCOUNT_OIDC_ID_TOKEN_ISSUER` | Keycloak realm URL (also used for JWKS) |
| `GITLAB_USER` / `GITLAB_USERPAT` | GitLab auth for private repos during build |
| `DEFAULT_HOME_PATH` | Redirect root `/` to this path if set |
| `POSTGRESQL_MAX_CONNECTIONS` | Override PostgreSQL max connections |
| `ALLOWED_DOCUMENT_TYPES` | Comma-separated list of allowed document extensions |