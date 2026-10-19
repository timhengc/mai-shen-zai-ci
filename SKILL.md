---
name: mcd-life-kit
description: 麦神在此｜万能麦麦助手。当前支持控卡：查询麦当劳餐品营养、核算一餐热量并对比预算。后续将扩展年报、喜好推荐与积分抽奖。
---

# 麦神在此｜万能麦麦助手

## 何时使用

用户提到控热量、减脂点餐、餐品热量、一餐会不会超标、麦当劳营养成分时使用本 Skill。

## 控卡流程

1. 若用户只想查某个餐品，搜索营养表并展示热量与宏量营养素。
2. 若用户给出一餐组合，按份数汇总总热量，并在有预算时判断是否超标。
3. 优先调用麦当劳 MCP 的 `list-nutrition-foods`；无 Token 时可用仓库 `examples/mock/nutrition.json` 演示。
4. 输出简洁表格 + 一句结论（未超标 / 已超标 / 可替换建议）。

## 命令参考

```bash
PYTHONPATH=src python3 -m mcd_life_kit.cli search <关键字> [--mock]
PYTHONPATH=src python3 -m mcd_life_kit.cli meal "<餐品1,餐品2>" [--budget 600] [--mock]
```

## 安全

- 不在对话或文件中写入真实 MCP Token
- 营养数据仅供参考，不构成医疗建议
