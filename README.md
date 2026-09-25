# 骑马钉小册子拼版 API（Saddle-Stitch Booklet Imposition API）

使用 Python + FastAPI 实现的骑马钉（对折装订）小册子拼版服务。输入**原稿总页数**和
**每册最多纸张数**，服务会：

1. 把连续原稿页按每册容量分册；
2. 将每册（实际只可能是最后一册）版面补齐到 **4 页的倍数**，补位页以空白（JSON `null`）表示；
3. 按纸张**从外到内**返回每张纸**正面（front）/反面（back）各自的左、右页码**，
   双面打印并对折后即可按原稿顺序翻阅。

> 1 张纸正反两面共 4 个版面，因此骑马钉册的页数永远是 4 的倍数。

---

## 1. 单条命令启动（Docker Compose）

前置要求：已安装 Docker（含 Compose 插件）。

```bash
docker compose up -d --build
```

依赖安装已纳入**容器启动流程**：`entrypoint.sh` 会在每次容器启动时先执行
`pip install -r requirements.txt`，随后启动 uvicorn（无需在构建镜像时预装依赖）。

停止服务：

```bash
docker compose down
```

查看启动日志（首次启动会先联网安装依赖）：

```bash
docker compose logs -f
```

## 2. 必要配置

所有配置均有默认值，直接 `docker compose up -d --build` 即可运行：

| 配置项 | 位置 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `HOST_PORT` | Compose 环境变量（宿主机） | `8000` | 宿主机映射端口。端口被占用时可临时改端口：`HOST_PORT=9000 docker compose up -d --build` |
| `PORT` | `docker-compose.yml` 容器环境变量 | `8000` | 容器内 uvicorn 监听端口，一般无需修改 |

如需持久化自定义端口，可在项目根目录创建 `.env` 文件：

```env
HOST_PORT=9000
```

## 3. API 地址与端口

服务默认监听 **8000 端口**：

| 用途 | 地址 |
| --- | --- |
| 健康检查 | http://localhost:8000/health |
| Swagger 交互文档 | http://localhost:8000/docs |
| ReDoc 文档 | http://localhost:8000/redoc |
| 拼版接口（POST） | `POST http://localhost:8000/api/v1/impose` |
| 拼版接口（GET 便捷形式，可直接在浏览器打开） | `GET http://localhost:8000/api/v1/impose?total_pages=16&max_sheets_per_booklet=4` |

## 4. 接口说明

### `POST /api/v1/impose`

**请求体（JSON）**

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `total_pages` | 整数 | 必填，正整数 `>= 1` | 原稿总页数 |
| `max_sheets_per_booklet` | 整数 | 必填，正整数 `>= 1` | 每册最多纸张数（每册最多 `4 ×` 该值 个版面） |

非正整数输入（`0`、负数、小数如 `16.5`、布尔值、数字字符串、缺失或多余字段）
一律返回 **HTTP 400** 及明确的中文错误说明。

请求示例：

```bash
curl -X POST http://localhost:8000/api/v1/impose \
  -H "Content-Type: application/json" \
  -d '{"total_pages": 16, "max_sheets_per_booklet": 4}'
```

响应示例（16 页、每册最多 4 张纸，共 1 册 4 张纸）：

```json
{
  "total_pages": 16,
  "max_sheets_per_booklet": 4,
  "booklet_count": 1,
  "total_sheets": 4,
  "booklets": [
    {
      "index": 0,
      "start_page": 1,
      "end_page": 16,
      "original_pages": 16,
      "padded_pages": 16,
      "blank_pages": 0,
      "sheet_count": 4,
      "sheets": [
        {
          "index": 0,
          "front": { "left": 16, "right": 1 },
          "back":  { "left": 2,  "right": 15 }
        },
        {
          "index": 1,
          "front": { "left": 14, "right": 3 },
          "back":  { "left": 4,  "right": 13 }
        },
        {
          "index": 2,
          "front": { "left": 12, "right": 5 },
          "back":  { "left": 6,  "right": 11 }
        },
        {
          "index": 3,
          "front": { "left": 10, "right": 7 },
          "back":  { "left": 8,  "right": 9 }
        }
      ]
    }
  ]
}
```

字段含义：

- `booklets[]`：分册结果，按装订顺序排列；`sheets[]` 为该册纸张，**`index: 0` 是最外侧一张**，依次向内。
- 每张纸给出 `front`（正面，朝外的一面）与 `back`（反面），各自包含 `left` / `right` 页码。
- 页码为**原稿 1-based 页码**；补位空白页用 **`null`** 表示。
- `start_page` / `end_page`：本册覆盖的原稿页区间；`original_pages` 原稿页数；
  `padded_pages` 补齐后页数（4 的倍数）；`blank_pages` 空白页数；`sheet_count` 用纸数。

### 空白页示例（5 页原稿）

5 页会补齐到 8 页（2 张纸），3 个空白页位于外封与内帖尾部：

```bash
curl -X POST http://localhost:8000/api/v1/impose \
  -H "Content-Type: application/json" \
  -d '{"total_pages": 5, "max_sheets_per_booklet": 10}'
```

```json
{
  "sheets": [
    { "index": 0, "front": { "left": null, "right": 1 }, "back": { "left": 2, "right": null } },
    { "index": 1, "front": { "left": null, "right": 3 }, "back": { "left": 4, "right": 5 } }
  ]
}
```

### 错误响应示例

```bash
curl -i -X POST http://localhost:8000/api/v1/impose \
  -H "Content-Type: application/json" \
  -d '{"total_pages": -4, "max_sheets_per_booklet": 2}'
```

```json
{
  "error": "invalid_input",
  "message": "输入参数校验失败：total_pages 与 max_sheets_per_booklet 必须是正整数。",
  "details": [
    { "field": "total_pages", "message": "必须为大于等于 1 的正整数。" }
  ]
}
```

## 5. 拼版规则（打印与装订说明）

对一册补齐到 `n` 页（`n` 为 4 的倍数）的小册子，从外到内第 `i` 张纸
（`i = 0, 1, …, n/4-1`）的版面为：

- 正面 front：左 `n − 2i`，右 `1 + 2i`
- 反面 back：左 `2 + 2i`，右 `n − 1 − 2i`

不变量：每张纸任一面左右页码之和恒为 `n + 1`；偶数页在左、奇数页在右。

打印时选择**双面打印、沿短边翻转（短边装订/flip on short edge）**，
全部印好后把整叠纸**横向对折（书脊在折缝处骑马钉装订）**，翻开顺序即为
1 → 2 → 3 → … 的原稿顺序。

**分册规则**：除最后一册外，每册都装满 `4 × max_sheets_per_booklet` 个版面；
剩余原稿页归入最后一册，并仅对该册补空白页到 4 的倍数。

## 6. 本地开发（不使用 Docker）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

运行测试：

```bash
# 核心算法测试仅依赖标准库，无需安装任何第三方包
python -m unittest tests.test_imposition -v

# 完整测试（含 API 层），需要先安装 requirements-dev.txt
python -m unittest discover -s tests -v
```

## 7. 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── imposition.py      # 分册 / 补齐 / 拼版核心算法（纯标准库）
│   ├── schemas.py         # Pydantic 请求与响应模型（正整数校验）
│   └── main.py            # FastAPI 路由与 400 错误处理
├── tests/
│   ├── test_imposition.py # 核心算法单元测试
│   └── test_api.py        # API 与非法输入测试
├── entrypoint.sh          # 容器入口：启动时安装依赖并启动服务
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```
