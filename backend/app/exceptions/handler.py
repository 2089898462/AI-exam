"""
FastAPI 统一异常处理器
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一处理业务异常"""
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
        },
    )