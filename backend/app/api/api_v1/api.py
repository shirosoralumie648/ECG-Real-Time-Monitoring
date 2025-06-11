from fastapi import APIRouter
from .endpoints import test, login, users

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(test.router, prefix="/test", tags=["test"])
