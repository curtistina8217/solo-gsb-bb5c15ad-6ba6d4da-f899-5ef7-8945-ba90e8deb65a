"""API 层测试（需先安装 requirements-dev.txt：fastapi / httpx）。

运行方式：
    pip install -r requirements-dev.txt
    python -m unittest discover -s tests -v
"""

import unittest

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestImposeEndpoint(unittest.TestCase):
    def test_valid_post_request(self):
        resp = client.post(
            "/api/v1/impose",
            json={"total_pages": 16, "max_sheets_per_booklet": 4},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_pages"], 16)
        self.assertEqual(data["booklet_count"], 1)
        self.assertEqual(data["total_sheets"], 4)
        outer = data["booklets"][0]["sheets"][0]
        self.assertEqual(outer["front"], {"left": 16, "right": 1})
        self.assertEqual(outer["back"], {"left": 2, "right": 15})

    def test_blank_page_is_null(self):
        resp = client.post(
            "/api/v1/impose",
            json={"total_pages": 5, "max_sheets_per_booklet": 10},
        )
        self.assertEqual(resp.status_code, 200)
        booklet = resp.json()["booklets"][0]
        self.assertEqual(booklet["blank_pages"], 3)
        self.assertEqual(booklet["sheets"][0]["front"]["left"], None)

    def test_get_equivalent(self):
        resp = client.get("/api/v1/impose?total_pages=8&max_sheets_per_booklet=2")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["booklets"][0]["sheets"][0]["front"], {"left": 8, "right": 1})

    def test_health(self):
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class TestInvalidInputs(unittest.TestCase):
    def _assert_400(self, payload):
        resp = client.post("/api/v1/impose", json=payload)
        self.assertEqual(resp.status_code, 400, payload)
        body = resp.json()
        self.assertEqual(body["error"], "invalid_input")
        self.assertIn("details", body)
        return body

    def test_zero_rejected(self):
        body = self._assert_400(
            {"total_pages": 0, "max_sheets_per_booklet": 2}
        )
        self.assertIn("total_pages", body["details"][0]["field"])

    def test_negative_rejected(self):
        self._assert_400({"total_pages": 16, "max_sheets_per_booklet": -1})

    def test_float_rejected(self):
        self._assert_400({"total_pages": 16.5, "max_sheets_per_booklet": 2})

    def test_integer_float_rejected(self):
        # 16.0 这类“看起来是整数”的浮点数也必须拒绝
        self._assert_400({"total_pages": 16.0, "max_sheets_per_booklet": 2})

    def test_string_rejected(self):
        self._assert_400({"total_pages": "16", "max_sheets_per_booklet": 2})

    def test_boolean_rejected(self):
        self._assert_400({"total_pages": True, "max_sheets_per_booklet": 2})

    def test_null_rejected(self):
        self._assert_400({"total_pages": None, "max_sheets_per_booklet": 2})

    def test_missing_field_rejected(self):
        self._assert_400({"total_pages": 16})

    def test_extra_field_rejected(self):
        self._assert_400(
            {"total_pages": 16, "max_sheets_per_booklet": 2, "duplex": True}
        )

    def test_get_invalid_query_rejected(self):
        resp = client.get("/api/v1/impose?total_pages=abc&max_sheets_per_booklet=2")
        self.assertEqual(resp.status_code, 400)
        resp = client.get("/api/v1/impose?total_pages=0&max_sheets_per_booklet=2")
        self.assertEqual(resp.status_code, 400)
        resp = client.get("/api/v1/impose?total_pages=16&max_sheets_per_booklet=2.5")
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
