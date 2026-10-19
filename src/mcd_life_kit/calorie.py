"""控卡能力：拉取营养表、搜索餐品、核算一餐热量。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mcp_client import MCPClient, MCPError
from .nutrition import FoodNutrition, MealSummary, build_meal, parse_nutrition_payload, search_foods

TOOL_NUTRITION = "list-nutrition-foods"
DEFAULT_MOCK = Path(__file__).resolve().parents[2] / "examples" / "mock" / "nutrition.json"


class CalorieCoach:
    def __init__(self, client: MCPClient | None = None, foods: list[FoodNutrition] | None = None) -> None:
        self.client = client
        self._foods = foods

    @classmethod
    def from_mock(cls, path: str | Path | None = None) -> "CalorieCoach":
        mock_path = Path(path) if path else DEFAULT_MOCK
        payload = json.loads(mock_path.read_text(encoding="utf-8"))
        return cls(foods=parse_nutrition_payload(payload))

    @classmethod
    def from_mcp(cls, token: str | None = None) -> "CalorieCoach":
        return cls(client=MCPClient(token=token))

    def load_foods(self, force: bool = False) -> list[FoodNutrition]:
        if self._foods is not None and not force:
            return self._foods
        if self.client is None:
            raise MCPError("未配置 MCP Client，也未提供本地营养数据。")
        payload = self.client.call_tool(TOOL_NUTRITION, {})
        foods = parse_nutrition_payload(_unwrap_data(payload))
        if not foods:
            raise MCPError("营养数据为空：请检查 list-nutrition-foods 返回。")
        self._foods = foods
        return foods

    def search(self, keyword: str, limit: int = 10) -> list[FoodNutrition]:
        return search_foods(self.load_foods(), keyword, limit=limit)

    def summarize_meal(self, specs: list[str], budget_kcal: float | None = None) -> tuple[MealSummary, list[str]]:
        return build_meal(self.load_foods(), specs, budget_kcal=budget_kcal)


def _unwrap_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def format_search(foods: list[FoodNutrition]) -> str:
    if not foods:
        return "没有找到匹配餐品。"
    lines = ["| 餐品 | 热量(kcal) | 蛋白(g) | 脂肪(g) | 碳水(g) | 钠(mg) |", "|---|---:|---:|---:|---:|---:|"]
    for food in foods:
        lines.append(
            f"| {food.name} | {food.kcal:.0f} | {food.protein:.1f} | {food.fat:.1f} | "
            f"{food.carbohydrate:.1f} | {food.sodium:.0f} |"
        )
    return "\n".join(lines)


def format_meal(summary: MealSummary, missing: list[str]) -> str:
    lines = ["## 控卡结果", ""]
    if summary.items:
        lines.append("| 餐品 | 份数 | 热量(kcal) | 蛋白(g) | 脂肪(g) | 碳水(g) |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for item in summary.items:
            lines.append(
                f"| {item.food.name} | {item.quantity:g} | {item.kcal:.0f} | "
                f"{item.protein:.1f} | {item.fat:.1f} | {item.carbohydrate:.1f} |"
            )
        lines.append("")
        lines.append(
            f"**合计**：{summary.total_kcal:.0f} kcal · 蛋白 {summary.total_protein:.1f}g · "
            f"脂肪 {summary.total_fat:.1f}g · 碳水 {summary.total_carbohydrate:.1f}g · "
            f"钠 {summary.total_sodium:.0f}mg"
        )
        if summary.budget_kcal is not None:
            remaining = summary.remaining_kcal or 0
            status = "未超标" if summary.within_budget else "已超标"
            lines.append(
                f"**预算**：{summary.budget_kcal:.0f} kcal · 剩余 {remaining:.0f} kcal · {status}"
            )
    else:
        lines.append("未能匹配到任何餐品。")

    if missing:
        lines.append("")
        lines.append("未匹配：" + "、".join(missing))
        lines.append("提示：先用 `search` 查准确餐品名，再用 `meal` 汇总。")
    return "\n".join(lines)
