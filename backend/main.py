#!/usr/bin/env python3
"""
FastAPI Backend for ML Education Platform
Main entry point for the application
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.db.database import init_db

from app.api import health, auth, content, tokens, tcoin, feedback, admin, course_sharing, course_management, course_user_sharing
from app.core.config import settings
from app.core.exception_handler import global_exception_handler

from redis import asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from app.services.scheduler_service import scheduler_service

import os
from pathlib import Path


ARQ_REDIS_SETTINGS = RedisSettings(host='localhost', port=6380)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理：
    - 启动时初始化数据库并创建 Redis 连接池
    - 关闭时优雅地释放 Redis 连接池

    这是 FastAPI 官方推荐的写法，用于替代已逐渐弃用的 @app.on_event('startup'/'shutdown')。
    """
    # --- startup ---
    print("正在初始化数据库...")
    await init_db()
    print("数据库初始化完成。")

    # 使用配置中的 Redis 主机和端口创建 ARQ 连接池
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )
    try:
        app.state.redis = await create_pool(redis_settings)
        print(f"Redis 连接池创建成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        # 不直接中断应用启动，交给依赖里的懒加载逻辑兜底
        print(f"⚠️ 创建 Redis 连接池失败，将在请求阶段按需重试: {e}")
        app.state.redis = None

    # 启动定时任务调度器
    print("正在启动定时任务调度器...")
    await scheduler_service.start_scheduler()
    print("定时任务调度器启动完成。")

    # 将控制权交还给 FastAPI（应用运行阶段）
    try:
        yield
    finally:
        # --- shutdown ---
        print("正在停止定时任务调度器...")
        await scheduler_service.stop_scheduler()
        print("定时任务调度器已停止。")

        redis = getattr(app.state, "redis", None)
        if redis:
            print("正在关闭 Redis 连接池...")
            await redis.close()
            print("Redis 连接池已关闭。")


# Create FastAPI instance
app = FastAPI(
    title="eachMaster Platform API",
    description="Backend API for automated machine learning education content generation",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# async def startup_event():
#     print("正在初始化数据库...")
#     await init_db()
#     print("数据库初始化完成。")
#     # 创建 ARQ 可用的 redis 池
#     app.state.redis = await create_pool(ARQ_REDIS_SETTINGS)

# @app.on_event("shutdown")
# async def shutdown_event():
#     if app.state.redis:
#         await app.state.redis.close()

# 依赖项，用于在路由中获取 redis 池
# async def get_redis():
#     return app.state.redis

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(request.method)
    if request.method == "OPTIONS":
        # 返回允许的 HTTP 方法和其他相关头部信息
        headers =  {
            "allow": "*",
            "Access-Control-Allow-Origin":"*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
        return JSONResponse(content=None,status_code=200,headers=headers)
    # 如果不是 OPTIONS 请求，则继续处理请求
    response = await call_next(request)
    # 确保所有响应都包含 CORS 头（作为备用，CORS 中间件应该已经添加了）
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response
    
static_dir = Path("static")
if static_dir.exists() and static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"静态文件目录不存在: {static_dir}")

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(content.router, prefix="/api/v1/content", tags=["content"])
app.include_router(tokens.router, prefix="/api/v1/tokens", tags=["Token Management"])
app.include_router(tcoin.router, prefix="/api/v1/tcoin", tags=["T-Coin Wallet"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Dashboard"])
app.include_router(course_sharing.router, prefix="/api/v1/course-sharing", tags=["Course Sharing"])
app.include_router(course_management.router, prefix="/api/v1/course-management", tags=["Course Management"])
app.include_router(course_user_sharing.router, prefix="/api/v1/course-user-sharing", tags=["Course User Sharing"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "ML Education Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.TESTING,
        log_level="info"
    )