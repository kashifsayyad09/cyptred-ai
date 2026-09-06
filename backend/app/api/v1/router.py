"""API v1 router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.v1 import auth, exams, sessions, events, risk, explain

api_router = APIRouter()

api_router.include_router(auth.router,     prefix="/auth",     tags=["Authentication"])
api_router.include_router(exams.router,    prefix="/exams",    tags=["Exams"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(events.router,   prefix="/events",   tags=["Events"])
api_router.include_router(risk.router,     prefix="/risk",     tags=["Risk"])
api_router.include_router(explain.router,                      tags=["Explanation"])
