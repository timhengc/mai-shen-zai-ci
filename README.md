# 麦麦生活套件 · mcd-life-kit

基于**麦当劳中国 MCP** 的一站式生活 Skill：控卡、年报、喜好推荐、积分抽奖。

> 麦当劳程序员创意开发大赛参赛作品 · 非麦当劳官方产品。  
> 餐品营养与价格以官方实时结果为准；输出仅供参考，不构成医疗建议。

## 为什么先做控卡？

| 模块 | 难度 | 依赖 | 本版状态 |
|---|---|---|---|
| **控卡** | 最低 | 仅 `list-nutrition-foods` | ✅ 已上线 |
| 年报 | 中 | 历史订单 | 🔜 下一步 |
| 喜好推荐 | 中高 | 订单记忆 + 菜单/核价 | 规划中 |
| 积分抽奖 | 低（但有写操作） | 抽奖 3 个 Tool | 规划中 |

控卡不依赖你有没有历史订单，**新号也能 demo**；营养数据又是后面「健康向推荐」的底座，所以最先落地。

## 一句话介绍

**告诉我这顿要吃什么，我用官方营养表算出总热量，并告诉你有没有超出预算。**

## 快速体验（免 Token）

```bash
# 搜索餐品
PYTHONPATH=src python3 -m mcd_life_kit.cli search 巨无霸 --mock

# 核算一餐（预算 600 kcal）
PYTHONPATH=src python3 -m mcd_life_kit.cli meal "巨无霸,中薯条,可口可乐 中杯" --budget 600 --mock
```

示例输出：合计 **1030 kcal**，预算 600 → **已超标**；换成「板烧鸡腿堡 + 无糖可乐」可压回预算内。

## 使用真实 MCP

1. 在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 申请 Token  
2. 配置环境变量：

```bash
export MCD_MCP_TOKEN=你的token
PYTHONPATH=src python3 -m mcd_life_kit.cli search 薯条
PYTHONPATH=src python3 -m mcd_life_kit.cli meal "麦香鸡,中薯条" --budget 700
```

MCP Client 配置见 [`mcp-config.example.json`](./mcp-config.example.json)。

## 目标用户

- 想吃麦当劳又想控热量 / 控钠的人
- 需要「先算再点」的减脂或轻食用户
- 后续：要看年度吃麦报告、要个性化推荐、要算抽奖值不值的会员

## 项目结构

```text
src/mcd_life_kit/
  mcp_client.py   # MCP 通用客户端（后续模块复用）
  nutrition.py    # 营养表解析
  calorie.py      # 控卡逻辑
  cli.py          # 命令行
examples/mock/    # 离线演示数据
MCP_INTEGRATION.md
CONTEST_DECLARATION.md
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 路线图

1. ✅ 控卡：搜索 + 一餐汇总 + 预算对比 + mock  
2. 年报：`order-list` 聚合消费 / 热量 / 高频单品  
3. 喜好推荐：口味记忆 × 营养约束 × 可售菜单  
4. 积分抽奖：期望值提示 + 确认后抽奖 + 奖品簿  

## 许可证

MIT（参赛声明见 `CONTEST_DECLARATION.md`）
