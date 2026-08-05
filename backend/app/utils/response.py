"""
统一 API 响应格式
"""
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi.responses import JSONResponse


def _serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


class ApiResponse:
    """统一 API 响应"""

    @staticmethod
    def success(data: Any = None, message: str = "success") -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=_serialize({
                "code": 200,
                "message": message,
                "data": data,
            }),
        )

    @staticmethod
    def error(code: int = 400, message: str = "error", data: Any = None) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content=_serialize({
                "code": code,
                "message": message,
                "data": data,
            }),
        )

    @staticmethod
    def created(data: Any = None, message: str = "created") -> JSONResponse:
        return JSONResponse(
            status_code=201,
            content=_serialize({
                "code": 201,
                "message": message,
                "data": data,
            }),
        )

    @staticmethod
    def paginated(
        items: list,
        total: int,
        page: int,
        page_size: int,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=_serialize({
                "code": 200,
                "message": "success",
                "data": {
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
            }),
        )
