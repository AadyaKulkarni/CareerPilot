from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import Base, engine
from app.models import *
from app.api.routes import router
from app.api.agents import router as agents_router

Base.metadata.create_all(bind=engine)
app=FastAPI(title=settings.app_name, version="1.0.0")
origins=[x.strip() for x in settings.backend_cors_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(router,prefix='/api')
app.include_router(agents_router,prefix='/api')
@app.get('/health')
def health(): return {"status":"ok","service":"placement-portal-api"}
