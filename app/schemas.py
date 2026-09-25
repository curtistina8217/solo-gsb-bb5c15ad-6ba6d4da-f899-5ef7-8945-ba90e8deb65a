"""请求 / 响应数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ImpositionRequest(BaseModel):
    """拼版请求。

    ``StrictInt`` 会拒绝布尔值、浮点数与数字字符串，只接受真正的整数；
    ``ge=1`` 进一步保证为正整数。
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    total_pages: StrictInt = Field(
        ..., ge=1, description="原稿总页数，必须为正整数。", examples=[16]
    )
    max_sheets_per_booklet: StrictInt = Field(
        ...,
        ge=1,
        description="每册最多纸张数（1 张纸正反 4 个版面），必须为正整数。",
        examples=[2],
    )


class SidePages(BaseModel):
    left: int | None = Field(..., description="左侧页码；null 表示空白页。")
    right: int | None = Field(..., description="右侧页码；null 表示空白页。")


class SheetLayout(BaseModel):
    index: int = Field(..., description="纸张序号，0 为最外侧纸张。")
    front: SidePages = Field(..., description="正面（朝外一面）左右页码。")
    back: SidePages = Field(..., description="反面（朝内一面）左右页码。")


class BookletLayout(BaseModel):
    index: int = Field(..., description="分册序号，从 0 开始。")
    start_page: int = Field(..., description="本册起始原稿页码（含）。")
    end_page: int = Field(..., description="本册结束原稿页码（含）。")
    original_pages: int = Field(..., description="本册原稿页数。")
    padded_pages: int = Field(..., description="补齐后的版面页数（4 的倍数）。")
    blank_pages: int = Field(..., description="补位空白页数。")
    sheet_count: int = Field(..., description="本册实际用纸张数。")
    sheets: list[SheetLayout] = Field(..., description="纸张列表，从外到内。")


class ImpositionResponse(BaseModel):
    total_pages: int
    max_sheets_per_booklet: int
    booklet_count: int = Field(..., description="分册数量。")
    total_sheets: int = Field(..., description="全部册合计用纸张数。")
    booklets: list[BookletLayout]
