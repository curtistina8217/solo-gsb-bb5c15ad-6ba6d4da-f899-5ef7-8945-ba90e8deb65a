"""拼版核心算法单元测试（仅依赖标准库，可直接 `python -m unittest` 运行）。"""

import unittest

from app.imposition import (
    build_imposition,
    find_reprint_sheets,
    impose_padded_booklet,
    split_booklets,
)


class TestSplitBooklets(unittest.TestCase):
    def test_single_booklet_within_capacity(self):
        ranges = split_booklets(total_pages=10, max_sheets_per_booklet=4)
        self.assertEqual(len(ranges), 1)
        self.assertEqual((ranges[0].start_page, ranges[0].end_page), (1, 10))
        self.assertEqual(ranges[0].padded_pages, 12)
        self.assertEqual(ranges[0].blank_pages, 2)
        self.assertEqual(ranges[0].sheet_count, 3)

    def test_exact_multiple_of_four_no_padding(self):
        ranges = split_booklets(total_pages=16, max_sheets_per_booklet=4)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].padded_pages, 16)
        self.assertEqual(ranges[0].blank_pages, 0)

    def test_multiple_booklets_only_last_is_padded(self):
        # 每册 2 张纸 = 8 页；17 页 -> 8 + 8 + 1
        ranges = split_booklets(total_pages=17, max_sheets_per_booklet=2)
        self.assertEqual(len(ranges), 3)
        self.assertEqual((ranges[0].start_page, ranges[0].end_page), (1, 8))
        self.assertEqual(ranges[0].padded_pages, 8)
        self.assertEqual(ranges[0].blank_pages, 0)
        self.assertEqual((ranges[1].start_page, ranges[1].end_page), (9, 16))
        self.assertEqual(ranges[1].padded_pages, 8)
        self.assertEqual(ranges[1].blank_pages, 0)
        self.assertEqual((ranges[2].start_page, ranges[2].end_page), (17, 17))
        self.assertEqual(ranges[2].padded_pages, 4)
        self.assertEqual(ranges[2].blank_pages, 3)
        self.assertEqual(ranges[0].index, 0)
        self.assertEqual(ranges[2].index, 2)

    def test_one_page_padded_to_four(self):
        ranges = split_booklets(total_pages=1, max_sheets_per_booklet=1)
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].padded_pages, 4)
        self.assertEqual(ranges[0].sheet_count, 1)

    def test_capacity_equal_multiple_of_four(self):
        # 总页数恰好装满两册
        ranges = split_booklets(total_pages=16, max_sheets_per_booklet=2)
        self.assertEqual(len(ranges), 2)
        self.assertEqual([r.original_pages for r in ranges], [8, 8])


class TestImposePaddedBooklet(unittest.TestCase):
    def test_four_sheets_classic_layout(self):
        # 16 页 / 4 张纸的经典骑马钉拼版
        sheets = impose_padded_booklet(16)
        self.assertEqual(len(sheets), 4)
        # 最外一张：正面 16|1，反面 2|15
        self.assertEqual(sheets[0]["front"], {"left": 16, "right": 1})
        self.assertEqual(sheets[0]["back"], {"left": 2, "right": 15})
        # 第二张：正面 14|3，反面 4|13
        self.assertEqual(sheets[1]["front"], {"left": 14, "right": 3})
        self.assertEqual(sheets[1]["back"], {"left": 4, "right": 13})
        # 第三张：正面 12|5，反面 6|11
        self.assertEqual(sheets[2]["front"], {"left": 12, "right": 5})
        self.assertEqual(sheets[2]["back"], {"left": 6, "right": 11})
        # 最内一张：正面 10|7，反面 8|9
        self.assertEqual(sheets[3]["front"], {"left": 10, "right": 7})
        self.assertEqual(sheets[3]["back"], {"left": 8, "right": 9})

    def test_single_sheet_padded(self):
        # 4 页 1 张纸
        sheets = impose_padded_booklet(4)
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0]["front"], {"left": 4, "right": 1})
        self.assertEqual(sheets[0]["back"], {"left": 2, "right": 3})

    def test_invalid_inputs(self):
        for bad in (0, -4, 6, 10):
            with self.assertRaises(ValueError):
                impose_padded_booklet(bad)


def _reading_order(sheets):
    """模拟对折后翻阅顺序：按纸张从外到内，依次取正面左、反面左、
    反面右、正面右（骑马钉嵌套书帖的物理翻阅序）。"""
    order = []
    for sheet in sheets:
        order.extend(
            [
                sheet["front"]["left"],
                sheet["back"]["left"],
                sheet["back"]["right"],
                sheet["front"]["right"],
            ]
        )
    return order


class TestFoldingReadingOrder(unittest.TestCase):
    """对折后的核心不变量：正反页码互补为 n+1，且偶数页始终在左、奇数页在右。"""

    def test_pair_sums_and_parity(self):
        for n in (4, 8, 12, 16, 20, 40):
            sheets = impose_padded_booklet(n)
            seen = set()
            for sheet in sheets:
                for side in ("front", "back"):
                    left, right = sheet[side]["left"], sheet[side]["right"]
                    self.assertEqual(left + right, n + 1, f"n={n} 左右页码之和应为 n+1")
                    self.assertEqual(left % 2, 0, "左页必为偶数页")
                    self.assertEqual(right % 2, 1, "右页必为奇数页")
                    seen.update((left, right))
            self.assertEqual(seen, set(range(1, n + 1)), f"n={n} 所有版面应恰好出现一次")

    def test_reading_order_of_a_sheet(self):
        # 单张纸（4 页）对折后翻阅顺序为 4,2,3,1：
        # 背面封面 4 -> 内左 2 -> 内右 3 -> 封面 1。
        # 内页正文顺序即 1(封面) -> 2 -> 3 -> 4(封底)。
        sheets = impose_padded_booklet(4)
        self.assertEqual(_reading_order(sheets), [4, 2, 3, 1])


class TestBuildImposition(unittest.TestCase):
    def test_16_pages_2_sheets_per_booklet_splits_and_maps_original_pages(self):
        result = build_imposition(total_pages=16, max_sheets_per_booklet=2)
        self.assertEqual(result["booklet_count"], 2)
        self.assertEqual(result["total_sheets"], 4)

        first = result["booklets"][0]
        self.assertEqual((first["start_page"], first["end_page"]), (1, 8))
        # 第 1 册 8 页 / 2 张纸
        self.assertEqual(first["sheets"][0]["front"], {"left": 8, "right": 1})
        self.assertEqual(first["sheets"][0]["back"], {"left": 2, "right": 7})
        self.assertEqual(first["sheets"][1]["front"], {"left": 6, "right": 3})
        self.assertEqual(first["sheets"][1]["back"], {"left": 4, "right": 5})

        second = result["booklets"][1]
        # 第 2 册页码从原稿第 9 页重新映射
        self.assertEqual((second["start_page"], second["end_page"]), (9, 16))
        self.assertEqual(second["sheets"][0]["front"], {"left": 16, "right": 9})
        self.assertEqual(second["sheets"][0]["back"], {"left": 10, "right": 15})

    def test_padding_blanks_are_null_and_contiguous_at_inner_end(self):
        # 5 页、1 张纸/册：仅 1 册，补齐到 8 页，3 个空白
        result = build_imposition(total_pages=5, max_sheets_per_booklet=10)
        booklet = result["booklets"][0]
        self.assertEqual(booklet["blank_pages"], 3)
        self.assertEqual(booklet["padded_pages"], 8)
        self.assertEqual(booklet["sheet_count"], 2)
        # 外纸：8(空)|1 / 2|7(空)
        self.assertEqual(booklet["sheets"][0]["front"], {"left": None, "right": 1})
        self.assertEqual(booklet["sheets"][0]["back"], {"left": 2, "right": None})
        # 内纸：6(空)|3 / 4|5
        self.assertEqual(booklet["sheets"][1]["front"], {"left": None, "right": 3})
        self.assertEqual(booklet["sheets"][1]["back"], {"left": 4, "right": 5})

    def test_single_page_booklet(self):
        result = build_imposition(total_pages=1, max_sheets_per_booklet=1)
        booklet = result["booklets"][0]
        self.assertEqual(booklet["blank_pages"], 3)
        # 4|1(原稿1) / 2(空)|3(空)
        self.assertEqual(booklet["sheets"][0]["front"], {"left": None, "right": 1})
        self.assertEqual(booklet["sheets"][0]["back"], {"left": None, "right": None})

    def test_every_original_page_appears_exactly_once(self):
        for total, cap in ((1, 1), (5, 2), (17, 2), (33, 3), (100, 4)):
            result = build_imposition(total_pages=total, max_sheets_per_booklet=cap)
            pages = []
            for booklet in result["booklets"]:
                for sheet in booklet["sheets"]:
                    for side in ("front", "back"):
                        for pos in ("left", "right"):
                            value = sheet[side][pos]
                            if value is not None:
                                pages.append(value)
            self.assertEqual(
                sorted(pages),
                list(range(1, total + 1)),
                f"total={total}, cap={cap}",
            )

    def test_summary_fields(self):
        result = build_imposition(total_pages=17, max_sheets_per_booklet=2)
        self.assertEqual(result["total_pages"], 17)
        self.assertEqual(result["max_sheets_per_booklet"], 2)
        self.assertEqual(result["booklet_count"], 3)
        self.assertEqual(result["total_sheets"], 2 + 2 + 1)


class TestFindReprintSheets(unittest.TestCase):
    def test_single_range_hits_one_sheet(self):
        # 16 页 / 4 张纸：第 3、4 页都在从外到内第 2 张纸（index 1）上
        result = find_reprint_sheets(16, 4, [(3, 4)])
        self.assertEqual(result["total_pages"], 16)
        self.assertEqual(result["max_sheets_per_booklet"], 4)
        self.assertEqual(result["damaged_page_count"], 2)
        self.assertEqual(result["reprint_sheet_count"], 1)
        sheet = result["sheets"][0]
        self.assertEqual(sheet["booklet_index"], 0)
        self.assertEqual(sheet["sheet_index"], 1)
        self.assertEqual(sheet["front"], {"left": 14, "right": 3})
        self.assertEqual(sheet["back"], {"left": 4, "right": 13})
        self.assertEqual(sheet["damaged_pages"], [3, 4])

    def test_overlapping_ranges_return_sheet_once(self):
        # 交叠区间 [1,3] 与 [2,5] 合并为受损页 {1,2,3,4,5}
        result = find_reprint_sheets(16, 4, [(1, 3), (2, 5)])
        self.assertEqual(result["damaged_page_count"], 5)
        self.assertEqual(result["reprint_sheet_count"], 3)
        self.assertEqual(
            [(s["booklet_index"], s["sheet_index"]) for s in result["sheets"]],
            [(0, 0), (0, 1), (0, 2)],
        )
        self.assertEqual(result["sheets"][0]["damaged_pages"], [1, 2])
        self.assertEqual(result["sheets"][1]["damaged_pages"], [3, 4])
        self.assertEqual(result["sheets"][2]["damaged_pages"], [5])

    def test_duplicate_range_still_returns_sheet_once(self):
        result = find_reprint_sheets(16, 4, [(3, 4), (3, 4)])
        self.assertEqual(result["reprint_sheet_count"], 1)
        self.assertEqual(result["sheets"][0]["damaged_pages"], [3, 4])

    def test_across_booklets_sorted_by_booklet_then_outer_to_inner(self):
        # 17 页、每册 2 张纸 -> 3 册（8 + 8 + 1 页，末册补 3 个空白页）
        result = find_reprint_sheets(17, 2, [(8, 10), (17, 17)])
        self.assertEqual(
            [(s["booklet_index"], s["sheet_index"]) for s in result["sheets"]],
            [(0, 0), (1, 0), (2, 0)],
        )
        first, second, third = result["sheets"]
        # 第 1 册最外一张纸：8|1 / 2|7，受损页 8
        self.assertEqual(first["front"], {"left": 8, "right": 1})
        self.assertEqual(first["back"], {"left": 2, "right": 7})
        self.assertEqual(first["damaged_pages"], [8])
        # 第 2 册最外一张纸：16|9 / 10|15，受损页 9、10
        self.assertEqual(second["front"], {"left": 16, "right": 9})
        self.assertEqual(second["back"], {"left": 10, "right": 15})
        self.assertEqual(second["damaged_pages"], [9, 10])
        # 第 3 册唯一一张纸：补白为 None，受损页 17
        self.assertEqual(third["front"], {"left": None, "right": 17})
        self.assertEqual(third["back"], {"left": None, "right": None})
        self.assertEqual(third["damaged_pages"], [17])

    def test_blank_pages_never_listed_as_damaged(self):
        # 5 页补齐到 8 页：空白页位置不应出现在 damaged_pages 中
        result = find_reprint_sheets(5, 10, [(1, 5)])
        self.assertEqual(result["reprint_sheet_count"], 2)
        for sheet in result["sheets"]:
            self.assertTrue(all(p is not None for p in sheet["damaged_pages"]))
        merged = sorted(p for s in result["sheets"] for p in s["damaged_pages"])
        self.assertEqual(merged, [1, 2, 3, 4, 5])

    def test_whole_book_damaged_reprints_every_sheet(self):
        result = find_reprint_sheets(17, 2, [(1, 17)])
        self.assertEqual(result["damaged_page_count"], 17)
        self.assertEqual(result["reprint_sheet_count"], 2 + 2 + 1)


if __name__ == "__main__":
    unittest.main()
