from fastapi import FastAPI,HTTPException
from fastapi.exceptions import RequestValidationError

from api.utils.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    ats_exception_handler,
)
from api.utils.exception import ATSException

from api.routes import resume_routes
from api.routes import parsing_routes
from api.routes import scoring_routes
from api.routes import ranking_routes
from api.routes import short_listing_routes
from api.routes import job_routes
from api.utils.logging_config import configure_logging

app=FastAPI(title="ZechPath AI recruitment", version="1.0.0")

app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    general_exception_handler,
)
app.add_exception_handler(
    ATSException,
    ats_exception_handler,
)

configure_logging()

app.include_router(resume_routes.router)
app.include_router(parsing_routes.router)
app.include_router(scoring_routes.router)
app.include_router(ranking_routes.router)
app.include_router(short_listing_routes.router)
app.include_router(job_routes.router)
 