"""请求 / 响应数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


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


class DamagedRange(BaseModel):
    """受损原稿页区间（1-based，端点均包含）。"""

    model_config = ConfigDict(extra="forbid")

    start_page: StrictInt = Field(
        ..., ge=1, description="受损起始页码（含），必须为正整数。", examples=[8]
    )
    end_page: StrictInt = Field(
        ..., ge=1, description="受损结束页码（含），必须为正整数。", examples=[10]
    )

    @model_validator(mode="after")
    def _check_not_inverted(self) -> "DamagedRange":
        if self.start_page > self.end_page:
            raise ValueError(
                f"区间倒置：start_page（{self.start_page}）不能大于 "
                f"end_page（{self.end_page}）。"
            )
        return self


class ReprintRequest(BaseModel):
    """补印定位请求：校验规则与拼版接口一致，另要求受损区间非空、
    不倒置且不超出 ``total_pages``。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    total_pages: StrictInt = Field(
        ..., ge=1, description="原稿总页数，必须为正整数。", examples=[17]
    )
    max_sheets_per_booklet: StrictInt = Field(
        ...,
        ge=1,
        description="每册最多纸张数（1 张纸正反 4 个版面），必须为正整数。",
        examples=[2],
    )
    damaged_ranges: list[DamagedRange] = Field(
        ...,
        min_length=1,
        description="受损原稿页区间列表，至少 1 项；区间允许交叠，同一纸张只返回一次。",
    )

    @model_validator(mode="after")
    def _check_within_total_pages(self) -> "ReprintRequest":
        for r in self.damaged_ranges:
            if r.end_page > self.total_pages:
                raise ValueError(
                    f"受损区间 [{r.start_page}, {r.end_page}] 越界："
                    f"原稿页码范围为 1..{self.total_pages}。"
                )
        return self


class ReprintSheet(BaseModel):
    booklet_index: int = Field(..., description="分册序号，从 0 开始。")
    sheet_index: int = Field(..., description="纸张序号，0 为该册最外侧纸张。")
    front: SidePages = Field(..., description="正面（朝外一面）左右页码。")
    back: SidePages = Field(..., description="反面（朝内一面）左右页码。")
    damaged_pages: list[int] = Field(
        ..., description="落在该纸上的受损原稿页码（升序、去重）。"
    )


class ReprintResponse(BaseModel):
    total_pages: int
    max_sheets_per_booklet: int
    damaged_page_count: int = Field(
        ..., description="合并交叠区间后的受损原稿页总数。"
    )
    reprint_sheet_count: int = Field(..., description="需要补印的纸张总数。")
    sheets: list[ReprintSheet] = Field(
        ..., description="需补印的纸张，按分册序号、纸张从外到内排序。"
    )
