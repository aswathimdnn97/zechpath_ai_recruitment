"""
main.py

ZechPath AI Recruitment - FastAPI application entry point.

Responsibilities
----------------
1. Initialize the FastAPI application.
2. Register global exception handlers.
3. Configure application logging.
4. Register recruitment, eligibility, and HR screening routers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from api.utils.error_handler import (
    ats_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from api.utils.exception import ATSException
from api.utils.logging_config import configure_logging

# Core ATS routers
from api.routes import (
    job_routes,
    parsing_routes,
    ranking_routes,
    resume_routes,
    scoring_routes,
    short_listing_routes,
)

# Recruitment and eligibility routers
from api.routes.recruitment_jobs_route import (
    router as recruitment_job_router,
)
from api.routes.eligibility_router import (
    router as eligibility_router,
)

# HR screening routers
from api.routes.hr_screening_router import (
    router as hr_screening_router,
)
from api.routes.hr_screenig_response_router import (
    router as hr_screening_response_router,
)
from api.routes.hr_screening_session_router import (
    router as hr_screening_session_router,
)
from api.routes.transcript_router import router as transcript_router


# ---------------------------------------------------------
# Application initialization
# ---------------------------------------------------------

app = FastAPI(
    title="ZechPath AI Recruitment",
    version="1.0.0",
)

# ---------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    ATSException,
    ats_exception_handler,
)

app.add_exception_handler(
    Exception,
    general_exception_handler,
)

# ---------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------

configure_logging()

# ---------------------------------------------------------
# Register ATS routers
# ---------------------------------------------------------

app.include_router(resume_routes.router)
app.include_router(parsing_routes.router)
app.include_router(scoring_routes.router)
app.include_router(ranking_routes.router)
app.include_router(short_listing_routes.router)
app.include_router(job_routes.router)

# Recruitment and eligibility
app.include_router(recruitment_job_router)
app.include_router(eligibility_router)

# HR screening
app.include_router(hr_screening_router)
app.include_router(hr_screening_response_router)
app.include_router(hr_screening_session_router)

#transcript
app.include_router(transcript_router)
