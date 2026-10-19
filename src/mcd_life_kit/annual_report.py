"""只读 MCP 年报：采集、去重、按北京时间聚合，输出脱敏报告。"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .mcp_client import MCPClient, MCPError
from .identity import make_identity, taste_scores

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path = ROOT / ".env") -> None:
    """读取 .env 与下载的 mcd-token.env；不执行 shell，不覆盖非空环境变量。"""
    paths = [path]
    if path == ROOT / ".env":
        paths.append(ROOT / "mcd-token.env")
    for config in paths:
        if not config.exists():
            continue
        for line in config.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key in {"MCD_MCP_TOKEN", "MCD_MCP_ENDPOINT"}:
                value = value.strip().strip("\"'")
                if value and not os.environ.get(key):
                    os.environ[key] = value


def pick(record: dict, *keys: str) -> Any:
    for key in keys:
        if record.get(key) is not None:
            return record[key]
    return None


def unpack(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            return unpack(json.loads(payload))
        except json.JSONDecodeError:
            raise MCPError("订单响应不是结构化 JSON，无法可靠统计；请保留响应格式并更新适配器。")
    if isinstance(payload, dict):
        if payload.get("success") is False or ("code" in payload and str(payload["code"]) not in {"0", "200", "0000"}):
            raise MCPError("订单查询业务失败，请检查 MCP 账户权限或登录状态。")
        if "data" in payload:
            return unpack(payload["data"])
    return payload


def records(payload: Any) -> tuple[list[dict], dict]:
    data = unpack(payload)
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict):
        for key in ("orders", "orderList", "list", "records", "items", "rows"):
            if isinstance(data.get(key), list):
                return data[key], data
    raise MCPError("未识别订单列表字段；为避免生成虚假空年报，已停止。")


def parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)) or re.fullmatch(r"\d{10,13}", str(value)):
            stamp = float(value)
            return datetime.fromtimestamp(stamp / 1000 if stamp > 1e11 else stamp, CST)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00").replace("/", "-"))
        return parsed.replace(tzinfo=CST) if parsed.tzinfo is None else parsed.astimezone(CST)
    except (ValueError, OverflowError, OSError):
        return None


def normalize_order(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    stamp = parse_date(pick(raw, "orderTime", "createTime", "createdAt", "orderDate", "orderCreateTime"))
    if stamp is None:
        return None
    status = str(pick(raw, "orderStatusName", "statusName", "orderStatusDesc", "statusDesc", "orderStatus", "status") or "未知")
    # 数字状态不猜测含义；只有明确已完成记录进入消费统计。
    completed = status.strip().lower() in {"completed", "complete", "finished", "done", "已完成", "交易完成", "订单完成", "订单已完成", "已取餐", "已送达", "取餐完成"}
    amount = None
    value = pick(raw, "realTotalAmount", "payAmount", "actualAmount", "actualPayAmount", "paidAmount", "totalPaid", "paymentAmount")
    if value is not None:
        try:
            number = Decimal(str(value))
            if number.is_finite() and number >= 0:
                amount = str(number.quantize(Decimal("0.01")))
        except InvalidOperation:
            pass
    # 只有显式分字段才换算；不靠金额大小猜单位。
    if amount is None and raw.get("payAmountFen") is not None:
        try:
            number = Decimal(str(raw["payAmountFen"])) / 100
            if number.is_finite() and number >= 0:
                amount = str(number.quantize(Decimal("0.01")))
        except InvalidOperation:
            pass
    foods = []
    def add_food(item: dict, multiplier: int = 1) -> None:
        if not isinstance(item, dict):
            return
        name = pick(item, "productName", "name", "mealName", "goodsName")
        qty = pick(item, "quantity", "qty", "count", "num")
        try:
            quantity = int(qty)
            if name and quantity > 0 and Decimal(str(qty)) == quantity:
                children = item.get("comboItemList")
                if isinstance(children, list) and children:
                    for child in children:
                        add_food(child, multiplier * quantity)
                else:
                    foods.append({"name": str(name), "quantity": quantity * multiplier})
        except (TypeError, ValueError, InvalidOperation):
            return
    for item in pick(raw, "orderProductList", "products", "items", "orderItems", "productList", "goodsList", "mealList") or []:
        add_food(item)
    return {"id": str(pick(raw, "orderId", "orderNo", "id") or ""), "time": stamp.isoformat(),
            "status": status, "completed": completed, "amount": amount, "foods": foods}


def _arguments(schema: dict, overrides: dict, page: int | None = None) -> dict:
    properties = schema.get("properties", {})
    result = dict(overrides)
    for name, spec in properties.items():
        if name in result:
            continue
        if name in {"page", "pageNo", "pageNum", "pageNumber", "current"} and page is not None:
            result[name] = page
        elif name in {"pageSize", "size", "limit"}:
            result[name] = min(50, spec.get("maximum", 50))
        elif "default" in spec:
            result[name] = spec["default"]
    missing = set(schema.get("required", [])) - result.keys()
    if missing:
        raise MCPError("MCP 需要额外参数 " + ", ".join(sorted(missing)) + "；用 --mcp-args JSON 显式提供。")
    unknown = result.keys() - properties.keys()
    if unknown and schema.get("additionalProperties") is False:
        raise MCPError("MCP 不支持参数：" + ", ".join(sorted(unknown)))
    return result


def collect_orders(client: MCPClient, overrides: dict | None = None, max_pages: int = 30) -> tuple[list[dict], list[str]]:
    tools = {tool["name"]: tool for tool in client.list_tools()}
    if "order-list" not in tools:
        raise MCPError("当前 MCP 未开放 order-list，无法拉取真实历史订单。")
    schema = tools["order-list"].get("inputSchema", {})
    pagination = any(key in schema.get("properties", {}) for key in ("page", "pageNo", "pageNum", "pageNumber", "current"))
    all_orders, warnings, seen_pages = [], [], set()
    for page in range(1, max_pages + 1):
        batch, meta = records(client.call_tool("order-list", _arguments(schema, overrides or {}, page)))
        fingerprint = json.dumps(batch, ensure_ascii=False, sort_keys=True)
        if fingerprint in seen_pages and batch:
            warnings.append("接口重复返回同一页，已停止翻页；数据可能不完整。")
            break
        seen_pages.add(fingerprint)
        all_orders.extend(batch)
        if not pagination or not batch or meta.get("hasMore") is False or meta.get("hasNext") is False:
            break
        total = pick(meta, "total", "totalCount")
        pages = pick(meta, "pages", "totalPages")
        if (total is not None and len(all_orders) >= int(total)) or (pages is not None and page >= int(pages)):
            break
    else:
        warnings.append(f"达到 {max_pages} 页查询上限，数据可能不完整。")
    return all_orders, warnings


def summarize(raw_orders: list[dict], year: int, *, demo: bool = False, warnings: list[str] | None = None) -> dict:
    normalized, seen = [], set()
    invalid = duplicates = no_id = 0
    for raw in raw_orders:
        order = normalize_order(raw)
        if order is None:
            invalid += 1
            continue
        if not order["id"]:
            no_id += 1
            continue
        if order["id"] in seen:
            duplicates += 1
            continue
        seen.add(order["id"])
        if datetime.fromisoformat(order["time"]).year == year:
            normalized.append(order)
    completed = sorted((o for o in normalized if o["completed"]), key=lambda o: o["time"])
    food_counts = Counter()
    months = [0] * 12
    hours = [0] * 24
    for order in completed:
        stamp = datetime.fromisoformat(order["time"])
        months[stamp.month - 1] += 1
        hours[stamp.hour] += 1
        for item in order["foods"]:
            food_counts[item["name"]] += item["quantity"]
    amounts = [Decimal(o["amount"]) for o in completed if o["amount"] is not None]
    notes = list(warnings or [])
    notes.append("官方 order-list 返回近期订单；本报告仅覆盖接口实际可见记录，不代表完整年度账单。")
    if invalid or no_id:
        notes.append(f"跳过 {invalid} 条日期不可识别、{no_id} 条缺少订单标识的记录。")
    unknown = sum(o["status"] not in {"已取消", "已退款", "cancelled", "canceled", "refunded", "待支付", "未支付"} and not o["completed"] for o in normalized)
    if unknown:
        notes.append(f"{unknown} 条订单状态未明确完成，未计入消费统计。")
    missing_foods = sum(not o["foods"] for o in completed)
    if missing_foods:
        notes.append(f"{missing_foods} 笔完成订单缺少可统计餐品明细，餐品排行仅统计已知明细。")
    if len(amounts) != len(completed):
        notes.append(f"实付金额覆盖 {len(amounts)}/{len(completed)} 笔完成订单；缺失金额不按 0 元计算。")
    return {"year": year, "demo": demo, "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
            "source": "离线合成示例 · 非真实消费" if demo else "麦当劳中国 MCP · order-list",
            "count": len(completed), "days": len({o["time"][:10] for o in completed}),
            "amount": str(sum(amounts, Decimal("0.00"))) if amounts else None,
            "amount_count": len(amounts), "months": months, "hours": hours,
            "top_foods": [{"name": name, "quantity": qty} for name, qty in food_counts.most_common(5)],
            "unique_foods": len(food_counts), "taste_scores": taste_scores(food_counts),
            "food_order_count": len(completed) - missing_foods,
            "first": completed[0]["time"][:10] if completed else None,
            "last": completed[-1]["time"][:10] if completed else None,
            "fetched": len(raw_orders), "deduplicated": duplicates, "excluded": len(normalized) - len(completed),
            "notes": notes}


def render_html(report: dict, nickname: str = "麦门同学", png_name: str = "annual-report.png") -> str:
    from .visuals import avatar_svg
    template = (Path(__file__).parent / "templates" / "annual_report.html").read_text(encoding="utf-8")
    # JSON 位于 script 中；转义 < 防止昵称或餐品名突破 script 标签。
    data = dict(report, identity=report.get("identity") or make_identity(report), nickname=nickname, png_name=png_name)
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    replacements = {"__REPORT_JSON__": encoded, "__REPORT_TITLE__": html.escape(f"{report['year']} 麦门年报"),
                    "__IDENTITY_AVATAR__": avatar_svg(data['identity'], nickname)}
    return re.sub('|'.join(map(re.escape, replacements)), lambda match: replacements[match[0]], template)


def generate_report(report: dict, output: Path, nickname: str = "麦门同学", png: bool = True) -> tuple[Path, Path | None]:
    if "identity" not in report:
        report = dict(report, identity=make_identity(report))
    output.mkdir(parents=True, exist_ok=True)
    html_path = output / "annual-report.html"
    html_path.write_text(render_html(report, nickname, "annual-report.png" if png else ""), encoding="utf-8")
    (output / "report-data.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    png_path = output / "annual-report.png"
    if png:
        try:
            subprocess.run(["node", str(ROOT / "scripts" / "export-report.cjs"), str(html_path.resolve()), str(png_path.resolve())], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise MCPError(f"HTML 已生成：{html_path}；PNG 导出失败。请安装 Node.js 并执行 npm ci 与 npx playwright install chromium，再重试。") from exc
    return html_path, png_path if png else None
