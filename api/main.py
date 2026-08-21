from fastapi import FastAPI
from api.routes import resume_routes
from api.routes import parsing_routes
from api.routes import scoring_routes
from api.routes import ranking_routes
from api.routes import short_listing_routes

app=FastAPI(title="ZechPath AI recruitment", version="1.0.0")

app.include_router(resume_routes.router)
app.include_router(parsing_routes.router)
app.include_router(scoring_routes.router)
app.include_router(ranking_routes.router)
app.include_router(short_listing_routes.router)
 