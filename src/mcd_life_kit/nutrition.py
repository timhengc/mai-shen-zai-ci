"""解析 ``list-nutrition-foods``，支持控卡查询与一餐汇总。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class FoodNutrition:
    name: str
    kcal: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carbohydrate: float = 0.0
    sodium: float = 0.0
    calcium: float = 0.0

    @property
    def known(self) -> bool:
        return any(
            (self.kcal, self.protein, self.fat, self.carbohydrate, self.sodium, self.calcium)
        )


def _as_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def _parse_table(text: str) -> list[FoodNutrition]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    header = lines[0]
    match = re.search(r"\{([^}]+)\}", header)
    if not match:
        return []
    columns = [part.strip() for part in match.group(1).split(",")]
    if len(columns) < 2:
        return []

    tail_size = len(columns) - 1
    metric_columns = columns[1:]
    foods: list[FoodNutrition] = []

    for line in lines[1:]:
        parts = [part.strip() for part in line.strip().split(",")]
        if len(parts) <= tail_size:
            continue
        name = ",".join(parts[: len(parts) - tail_size]).strip()
        tail = parts[len(parts) - tail_size :]
        record = dict(zip(metric_columns, tail))
        if not name:
            continue
        foods.append(
            FoodNutrition(
                name=name,
                kcal=_as_float(record.get("energyKcal")),
                protein=_as_float(record.get("protein")),
                fat=_as_float(record.get("fat")),
                carbohydrate=_as_float(record.get("carbohydrate")),
                sodium=_as_float(record.get("sodium")),
                calcium=_as_float(record.get("calcium")),
            )
        )
    return foods


def _parse_records(records: list[Any]) -> list[FoodNutrition]:
    foods: list[FoodNutrition] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        name = record.get("productName") or record.get("name")
        if not name:
            continue
        foods.append(
            FoodNutrition(
                name=str(name),
                kcal=_as_float(record.get("energyKcal")),
                protein=_as_float(record.get("protein")),
                fat=_as_float(record.get("fat")),
                carbohydrate=_as_float(record.get("carbohydrate")),
                sodium=_as_float(record.get("sodium")),
                calcium=_as_float(record.get("calcium")),
            )
        )
    return foods


def parse_nutrition_payload(payload: Any) -> list[FoodNutrition]:
    """兼容文本表 / JSON 数组 / ``{data: ...}`` 等多种返回形态。"""
    if payload is None:
        return []
    if isinstance(payload, str):
        text = payload.strip()
        if text.startswith("[") or text.startswith("{"):
            try:
                return parse_nutrition_payload(json.loads(text))
            except json.JSONDecodeError:
                pass
        return _parse_table(payload)
    if isinstance(payload, list):
        return _parse_records(payload)
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        if isinstance(data, str):
            return parse_nutrition_payload(data)
        if isinstance(data, list):
            return _parse_records(data)
        if isinstance(data, dict):
            # 少数实现把表塞在 data.list / data.foods
            for key in ("list", "foods", "items", "records"):
                if isinstance(data.get(key), list):
                    return _parse_records(data[key])
    return []


def search_foods(foods: Iterable[FoodNutrition], keyword: str, limit: int = 10) -> list[FoodNutrition]:
    key = (keyword or "").strip().lower()
    if not key:
        return list(foods)[:limit]
    hits = [food for food in foods if key in food.name.lower()]
    return hits[:limit]


def match_food(foods: Iterable[FoodNutrition], name: str) -> FoodNutrition | None:
    target = (name or "").strip().lower()
    if not target:
        return None
    exact = [food for food in foods if food.name.lower() == target]
    if exact:
        return exact[0]
    contains = [food for food in foods if target in food.name.lower()]
    if len(contains) == 1:
        return contains[0]
    # 取最短名称（通常更接近单品名）
    if contains:
        return sorted(contains, key=lambda food: len(food.name))[0]
    return None


@dataclass
class MealItem:
    food: FoodNutrition
    quantity: float = 1.0

    @property
    def kcal(self) -> float:
        return self.food.kcal * self.quantity

    @property
    def protein(self) -> float:
        return self.food.protein * self.quantity

    @property
    def fat(self) -> float:
        return self.food.fat * self.quantity

    @property
    def carbohydrate(self) -> float:
        return self.food.carbohydrate * self.quantity

    @property
    def sodium(self) -> float:
        return self.food.sodium * self.quantity


@dataclass
class MealSummary:
    items: list[MealItem]
    budget_kcal: float | None = None

    @property
    def total_kcal(self) -> float:
        return sum(item.kcal for item in self.items)

    @property
    def total_protein(self) -> float:
        return sum(item.protein for item in self.items)

    @property
    def total_fat(self) -> float:
        return sum(item.fat for item in self.items)

    @property
    def total_carbohydrate(self) -> float:
        return sum(item.carbohydrate for item in self.items)

    @property
    def total_sodium(self) -> float:
        return sum(item.sodium for item in self.items)

    @property
    def remaining_kcal(self) -> float | None:
        if self.budget_kcal is None:
            return None
        return self.budget_kcal - self.total_kcal

    @property
    def within_budget(self) -> bool | None:
        remaining = self.remaining_kcal
        if remaining is None:
            return None
        return remaining >= 0


def build_meal(
    foods: Iterable[FoodNutrition],
    specs: list[str],
    budget_kcal: float | None = None,
) -> tuple[MealSummary, list[str]]:
    """解析 ``巨无霸×1,中薯条,可乐`` 一类规格，返回汇总与未匹配项。"""
    catalog = list(foods)
    items: list[MealItem] = []
    missing: list[str] = []

    for raw in specs:
        piece = raw.strip()
        if not piece:
            continue
        quantity = 1.0
        name = piece
        if "×" in piece:
            name, _, qty = piece.partition("×")
            quantity = _as_float(qty) or 1.0
        elif "x" in piece.lower() and re.search(r"[xX]\s*\d+(\.\d+)?\s*$", piece):
            name, qty = re.split(r"[xX]", piece, maxsplit=1)
            quantity = _as_float(qty) or 1.0
        food = match_food(catalog, name.strip())
        if food is None:
            missing.append(piece)
            continue
        items.append(MealItem(food=food, quantity=quantity))

    return MealSummary(items=items, budget_kcal=budget_kcal), missing
