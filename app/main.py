from fastapi import FastAPI

from app.config import settings
from app.routers.health import router as health_router
from app.routers.companies import router as companies_router
from app.routers.assessments import router as assessments_router
from app.routers.dimension import router as dimension_router, scores_router
from app.routers.documents import router as documents_router
from app.routers.signals import router as signals_router
from app.routers.culture import router as culture_router  # ← ADD THIS
from app.routers.board import router as board_router
from app.routers.scoring import router as scoring_router
from app.routers.search import router as search_router
from app.routers.justification import router as justification_router
from app.routers.evidence import router as evidence_router
<<<<<<< HEAD
from app.routers.analyst_notes import router as analyst_notes_router
=======
>>>>>>> 011acc3 (feat: onboard any company pipeline)
from app.routers.pipeline import router as pipeline_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    app.include_router(health_router)
    app.include_router(companies_router, prefix="/api/v1")
    app.include_router(assessments_router, prefix="/api/v1")
    app.include_router(dimension_router, prefix="/api/v1")
    app.include_router(scores_router, prefix="/api/v1")
    app.include_router(documents_router)
    app.include_router(signals_router, prefix="/api/v1")
    app.include_router(culture_router, prefix="/api/v1")  # ← ADD THIS
    app.include_router(board_router, prefix="/api/v1")
    app.include_router(scoring_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(justification_router, prefix="/api/v1")
    app.include_router(evidence_router, prefix="/api/v1")
<<<<<<< HEAD
    app.include_router(analyst_notes_router, prefix="/api/v1")
=======
>>>>>>> 011acc3 (feat: onboard any company pipeline)
    app.include_router(pipeline_router, prefix="/api/v1")

    return app


app = create_app()