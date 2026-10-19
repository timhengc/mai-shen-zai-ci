# 麦神在此｜点进来，赐予你麦门神力

> **万能麦麦助手** · 控卡 / 年报 / 喜好推荐 / 积分抽奖，一站疯癫到底。  
> 别问中午吃啥。问麦神。

麦当劳程序员创意开发大赛参赛作品 · 基于 [麦当劳中国 MCP](https://github.com/M-China/mcd-mcp-server) · 非官方产品。  
餐品营养与价格以官方实时结果为准；输出仅供参考，不构成医疗建议。

---

## 这是什么

你的大脑在加班、约会、减脂、省钱之间反复横跳？  
**麦神**接管决策：算热量、翻年报、记喜好、掂抽奖——把点麦从纠结变成仪式。

| 神力 | 状态 | 一句话 |
|---|---|---|
| **控卡审判** | ✅ 已觉醒 | 报菜名，立刻算出这顿会不会热量爆炸 |
| **麦门年报** | 🔜 降临中 | 你究竟向巨无霸献祭了多少次 |
| **喜好神谕** | 规划中 | 越吃越懂你，越懂越想点 |
| **积分狂抽** | 规划中 | 先算值不值，再决定要不要疯一次 |

仓库名 / 参赛 Issue 标题你可最终拍板；产品内核先按「万能麦麦助手」推进。

## 30 秒感受神力（免 Token）

```bash
# 搜餐品
PYTHONPATH=src python3 -m mcd_life_kit.cli search 巨无霸 --mock

# 审判一餐（预算 600 kcal）
PYTHONPATH=src python3 -m mcd_life_kit.cli meal "巨无霸,中薯条,可口可乐 中杯" --budget 600 --mock
```

巨无霸套餐合计约 **1030 kcal** → 预算 600 → **已超标**。麦神不会骗你。

## 接入真实 MCP

1. 在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 申请 Token  
2. 配置后召唤：

```bash
export MCD_MCP_TOKEN=你的token
PYTHONPATH=src python3 -m mcd_life_kit.cli search 薯条
PYTHONPATH=src python3 -m mcd_life_kit.cli meal "麦香鸡,中薯条" --budget 700
```

配置示例：[`mcp-config.example.json`](./mcp-config.example.json) · 集成说明：[`MCP_INTEGRATION.md`](./MCP_INTEGRATION.md)

## 目标用户

- 想吃麦当劳又想控热量的分裂人格青年
- 需要年度吃麦报告给自己一点震撼教育的人
- 券、积分、抽奖算不清楚但仍想赢的赌徒型会员

## 项目结构

```text
src/mcd_life_kit/
  mcp_client.py   # MCP 通用客户端（全模块复用）
  nutrition.py    # 营养表解析
  calorie.py      # 控卡审判
  cli.py          # 命令行
examples/mock/    # 离线演示
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 许可证

MIT · 参赛声明见 [`CONTEST_DECLARATION.md`](./CONTEST_DECLARATION.md)
