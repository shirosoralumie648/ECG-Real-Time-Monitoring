from fastapi import APIRouter
from .endpoints import test, login, users, websocket

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(websocket.router, prefix="", tags=["websockets"])
api_router.include_router(test.router, prefix="/test", tags=["test"])
