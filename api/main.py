from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from api import routers

app = FastAPI(
    title="x-ui REST API",
    description=(
        "## Overview\n"
        "This API provides programmatic access to the 3x-ui management system. "
        "It interacts directly with the `x-ui.db` SQLite database.\n\n"
        "### ⚠️ Read-Only Fields\n"
        "The following fields are **automatically updated by the 3x-ui panel** (via xray-core) "
        "every second and are **read-only** via this API:\n"
        "- `up`, `down`, `all_time` (Traffic counters)\n"
        "- `last_online` (Timestamp)\n"
        "- The entire `inbound_client_ips` and `outbound_traffics` tables.\n\n"
        "### 🛡️ Read-Only API\n"
        "This API is **entirely read-only**. All management operations must be performed via the 3x-ui web panel.\n\n"
        "### 📊 Client Activity Tracking\n"
        "The `/clients` endpoints expose data collected from the xray access log — "
        "including per-client IPs, connection destinations, and protocols used."
    ),
    version="2.1.0",
    contact={
        "name": "x-ui API Support",
        "url": "https://github.com/M3hran/x-ui",
    },
    docs_url=None,  # We will define custom routes for these
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)

# ── Custom Docs Routes ──────────────────────────────────────────
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )

# ── Register routers ──────────────────────────────────────────────
app.include_router(routers.client_traffics,   prefix="/api/v1")
app.include_router(routers.client_ips,        prefix="/api/v1")
app.include_router(routers.outbound_traffics, prefix="/api/v1")
app.include_router(routers.clients,           prefix="/api/v1")
app.include_router(routers.settings,          prefix="/api/v1")
app.include_router(routers.users,             prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "x-ui API is running", "version": "2.1.0"}
