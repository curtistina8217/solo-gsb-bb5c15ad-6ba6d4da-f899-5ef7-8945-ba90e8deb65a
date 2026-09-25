"""FastAPI 入口：骑马钉小册子拼版 API。"""

from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .imposition import build_imposition, find_reprint_sheets
from .schemas import (
    ImpositionRequest,
    ImpositionResponse,
    ReprintRequest,
    ReprintResponse,
)

app = FastAPI(
    title="骑马钉小册子拼版 API",
    description=(
        "输入原稿总页数与每册最多纸张数，按骑马钉（对折装订）方式分册拼版，"
        "返回每张纸正反面各自的左、右页码；补位页以 null（空白）表示。"
        "另提供补印定位接口：给定受损原稿页区间，找出需要整张重印的纸。"
    ),
    version="1.1.0",
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
        elif err_type == "too_short":
            message = "受损页区间列表不能为空，至少需要 1 项。"
        elif err_type in {"list_type", "model_type", "dict_type"}:
            message = (
                "格式不正确：damaged_ranges 必须为对象数组，"
                "每项含 start_page 与 end_page。"
            )
        elif err_type == "value_error":
            # 自定义校验器（区间倒置 / 越界）抛出的信息，去掉 Pydantic 前缀
            message = message.removeprefix("Value error, ")

        formatted.append({"field": field, "message": message})
    return formatted


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """非正整数 / 类型错误 / 区间倒置或越界等统一返回 HTTP 400 与明确错误信息。"""
    if request.url.path == "/api/v1/reprint":
        message = (
            "输入参数校验失败：total_pages 与 max_sheets_per_booklet 必须是正整数，"
            "damaged_ranges 至少含 1 个不倒置且不越界的受损页区间。"
        )
    else:
        message = (
            "输入参数校验失败：total_pages 与 max_sheets_per_booklet 必须是正整数。"
        )
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_input",
            "message": message,
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
        "reprint_endpoint": "/api/v1/reprint",
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


@app.post(
    "/api/v1/reprint",
    response_model=ReprintResponse,
    tags=["imposition"],
    summary="受损页补印定位",
)
async def reprint(payload: ReprintRequest) -> ReprintResponse:
    """按现有分册与拼版规则，找出覆盖受损原稿页、需要整张重印的纸。

    受损区间允许交叠，同一纸张只返回一次；结果按分册序号、
    纸张从外到内排序。区间倒置、越界或列表为空返回 HTTP 400。
    """
    result = find_reprint_sheets(
        total_pages=payload.total_pages,
        max_sheets_per_booklet=payload.max_sheets_per_booklet,
        damaged_ranges=[
            (r.start_page, r.end_page) for r in payload.damaged_ranges
        ],
    )
    return ReprintResponse.model_validate(result)
