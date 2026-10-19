"""命令行入口。

示例：
  python -m mcd_life_kit.cli search 巨无霸 --mock
  python -m mcd_life_kit.cli meal 巨无霸,中薯条,可口可乐 --budget 600 --mock
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许直接 python src/... 运行
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from mcd_life_kit.calorie import CalorieCoach, format_meal, format_search  # noqa: E402
from mcd_life_kit.mcp_client import MCPError  # noqa: E402


def _coach(args: argparse.Namespace) -> CalorieCoach:
    if args.mock:
        return CalorieCoach.from_mock(args.mock_data)
    return CalorieCoach.from_mcp(token=args.token)


def cmd_search(args: argparse.Namespace) -> int:
    coach = _coach(args)
    foods = coach.search(args.keyword, limit=args.limit)
    print(format_search(foods))
    print(f"\n共 {len(foods)} 条（本地目录共 {len(coach.load_foods())} 个餐品）")
    return 0


def cmd_meal(args: argparse.Namespace) -> int:
    coach = _coach(args)
    specs = [part.strip() for part in args.items.replace("，", ",").split(",") if part.strip()]
    summary, missing = coach.summarize_meal(specs, budget_kcal=args.budget)
    print(format_meal(summary, missing))
    return 0 if not missing else 2


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--token", default=None, help="MCP Token（默认读 MCD_MCP_TOKEN）")
    common.add_argument("--mock", action="store_true", help="使用本地 mock 营养数据，无需 Token")
    common.add_argument("--mock-data", default=None, help="自定义 mock JSON 路径")

    parser = argparse.ArgumentParser(
        prog="mcd-life-kit",
        description="麦麦生活套件 · 当前模块：控卡（营养查询 / 一餐热量核算）",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="按关键字搜索餐品营养", parents=[common])
    search.add_argument("keyword", help="餐品关键字，如：巨无霸 / 薯条 / 可乐")
    search.add_argument("--limit", type=int, default=10)
    search.set_defaults(func=cmd_search)

    meal = sub.add_parser("meal", help="核算一餐热量", parents=[common])
    meal.add_argument(
        "items",
        help="餐品列表，逗号分隔，支持份数：巨无霸,中薯条×2,可口可乐",
    )
    meal.add_argument("--budget", type=float, default=None, help="本餐热量预算（kcal）")
    meal.set_defaults(func=cmd_meal)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except MCPError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"错误：找不到文件 {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
