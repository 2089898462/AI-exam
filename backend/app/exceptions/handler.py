"""
FastAPI 统一异常处理器

所有异常返回统一格式：
{
    "code": <HTTP状态码>,
    "message": "<错误描述>",
    "data": <附加数据>,
    "request_id": "<请求追踪ID>",
    "trace_id": "<链路追踪ID>"
}
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger
from app.core.request_logging import get_request_id, get_trace_id
from app.exceptions import AppException

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """统一处理业务异常

    业务异常记录 WARNING 级别日志，包含 trace_id 和 request_id 方便追踪。
    """
    request_id = get_request_id(request)
    trace_id = get_trace_id(request)

    log_msg = (
        f"[APP_ERROR] trace_id={trace_id} | id={request_id} | code={exc.code} | "
        f"message={exc.message} | path={request.url.path}"
    )
    if exc.code >= 500:
        logger.error(log_msg)
    elif exc.code >= 400:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": exc.data,
            "request_id": request_id,
            "trace_id": trace_id,
        },
    )