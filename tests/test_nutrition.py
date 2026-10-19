import json
import unittest
from pathlib import Path

from mcd_life_kit.calorie import CalorieCoach, format_meal
from mcd_life_kit.nutrition import build_meal, parse_nutrition_payload, search_foods

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "examples" / "mock" / "nutrition.json"


class NutritionTests(unittest.TestCase):
    def setUp(self) -> None:
        payload = json.loads(MOCK.read_text(encoding="utf-8"))
        self.foods = parse_nutrition_payload(payload)

    def test_parse_count(self) -> None:
        self.assertEqual(len(self.foods), 8)
        big_mac = next(food for food in self.foods if food.name == "巨无霸")
        self.assertEqual(big_mac.kcal, 550)

    def test_search(self) -> None:
        hits = search_foods(self.foods, "巨无霸")
        self.assertEqual(hits[0].name, "巨无霸")

    def test_meal_budget(self) -> None:
        summary, missing = build_meal(
            self.foods, ["巨无霸", "中薯条", "可口可乐 中杯"], budget_kcal=600
        )
        self.assertEqual(missing, [])
        self.assertAlmostEqual(summary.total_kcal, 550 + 340 + 140)
        self.assertFalse(summary.within_budget)

    def test_coach_mock(self) -> None:
        coach = CalorieCoach.from_mock(MOCK)
        summary, missing = coach.summarize_meal(["板烧鸡腿堡", "无糖可口可乐 中杯"], budget_kcal=500)
        self.assertEqual(missing, [])
        self.assertTrue(summary.within_budget)
        text = format_meal(summary, missing)
        self.assertIn("未超标", text)


if __name__ == "__main__":
    unittest.main()
