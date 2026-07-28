from fastapi import APIRouter

from app.api.routers.health import router as health_router
from app.api.routers.chat import router as chat_router


# 创建 API 总路由，集中管理所以子路由
api_router = APIRouter()

# 注册健康检查子路由
api_router.include_router(health_router)

# 注册聊天子路由
api_router.include_router(chat_router)