"""FastAPI 入口：骑马钉小册子拼版 API。"""

from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .imposition import build_imposition
from .schemas import ImpositionRequest, ImpositionResponse

app = FastAPI(
    title="骑马钉小册子拼版 API",
    description=(
        "输入原稿总页数与每册最多纸张数，按骑马钉（对折装订）方式分册拼版，"
        "返回每张纸正反面各自的左、右页码；补位页以 null（空白）表示。"
    ),
    version="1.0.0",
)


def _format_validation_errors(errors: list[dict]) -> list[dict]:
    """把 Pydantic 校验错误整理成简洁的中文说明。"""
    formatted: list[dict] = []
    for err in errors:
        loc = [
            str(part)
            for part in err.get("loc", [])
            if part not in ("body", "query")
        ]
        field = ".".join(loc) if loc else "请求体"
        err_type = err.get("type", "")
        message = err.get("msg", "参数不合法。")

        if err_type in {
            "int_type",
            "int_parsing",
            "strict_int",
            "int_from_float",
            "bool_type",
        }:
            message = "必须为正整数（不接受小数、布尔值、字符串或空值）。"
        elif err_type in {"greater_than_equal", "ge"}:
            message = "必须为大于等于 1 的正整数。"
        elif err_type == "extra_forbidden":
            message = "存在不支持的多余字段。"
        elif err_type == "missing":
            message = "缺少必填参数。"

        formatted.append({"field": field, "message": message})
    return formatted


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """非正整数 / 类型错误统一返回 HTTP 400 与明确错误信息。"""
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_input",
            "message": "输入参数校验失败：total_pages 与 max_sheets_per_booklet 必须是正整数。",
            "details": _format_validation_errors(exc.errors()),
        },
    )


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "saddle-stitch-imposition",
        "docs": "/docs",
        "health": "/health",
        "impose_endpoint": "/api/v1/impose",
    }


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/api/v1/impose",
    response_model=ImpositionResponse,
    tags=["imposition"],
    summary="骑马钉拼版",
)
async def impose(payload: ImpositionRequest) -> ImpositionResponse:
    result = build_imposition(
        total_pages=payload.total_pages,
        max_sheets_per_booklet=payload.max_sheets_per_booklet,
    )
    return ImpositionResponse.model_validate(result)


@app.get(
    "/api/v1/impose",
    response_model=ImpositionResponse,
    tags=["imposition"],
    summary="骑马钉拼版（GET 便捷形式，可直接在浏览器中查看）",
)
async def impose_get(
    total_pages: int = Query(..., ge=1, description="原稿总页数，正整数。"),
    max_sheets_per_booklet: int = Query(
        ..., ge=1, description="每册最多纸张数，正整数。"
    ),
) -> ImpositionResponse:
    # 查询参数的类型 / 范围错误同样由 validation_exception_handler 统一返回 400。
    result = build_imposition(total_pages, max_sheets_per_booklet)
    return ImpositionResponse.model_validate(result)
