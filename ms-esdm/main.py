import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.session import Base, sync_engine
from routes.routes import api_router
from services.esdm_auth import auto_login

DISABLE_LICENSE = os.getenv("DISABLE_LICENSE", "false").lower() == "true"

app = FastAPI(
    title="ESDM API",
    root_path="/api",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

license_service = None

if not DISABLE_LICENSE:
    from licensing.service import LicenseService
    from licensing.exceptions import LicenseInvalid

    LICENSE_PATH = os.getenv("LICENSE_PATH", "license/license.json")
    from db.license_repo import LicenseRepository
    license_repo = LicenseRepository(sync_engine)
    license_service = LicenseService(
        db=license_repo,
        license_path=LICENSE_PATH
    )


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=sync_engine)

    if not DISABLE_LICENSE and license_service is not None:
        try:
            license_service.validate_startup()
        except Exception as e:
            raise RuntimeError(f"License validation failed: {str(e)}")

    auto_login()


@app.middleware("http")
async def license_middleware(request, call_next):
    if not DISABLE_LICENSE and license_service is not None:
        try:
            license_service.validate_request()
        except Exception as e:
            return JSONResponse(
                status_code=403,
                content={"detail": str(e)}
            )
    return await call_next(request)


@app.get("/license/status", tags=["License"])
def license_status():
    if DISABLE_LICENSE or license_service is None:
        return {"status": "licensing disabled"}
    return license_service.status()


app.include_router(api_router)
