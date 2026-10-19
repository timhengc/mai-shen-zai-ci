# MCP 集成说明

## 使用的麦当劳 MCP Server

- 接入地址：`https://mcp.mcd.cn`
- 协议：Streamable HTTP + JSON-RPC 2.0
- 鉴权：`Authorization: Bearer <MCP Token>`
- 配置示例：见 [`mcp-config.example.json`](./mcp-config.example.json)

## 当前版本实际调用的 Tool

| Tool | 用途 |
|---|---|
| `list-nutrition-foods` | 拉取官方餐品营养表，用于控卡查询与一餐热量汇总 |

## 调用流程（控卡）

1. 用户给出餐品关键字，或给出一餐组合（可带预算 kcal）
2. Skill / CLI 调用 `list-nutrition-foods`
3. 解析返回的营养表（兼容文本表与结构化 JSON）
4. 搜索匹配餐品，或按份数汇总热量 / 蛋白 / 脂肪 / 碳水 / 钠
5. 若设置预算，输出是否超标与剩余额度

## 业务价值

把「今天这顿麦当劳会不会热量爆炸」变成可计算答案，而不是凭感觉点餐。  
后续模块（年报、喜好推荐、积分抽奖）将复用同一套 MCP 客户端，并扩展：

- `order-list` / `query-order` → 年报与口味记忆
- `query-meals` / `calculate-price` / `query-store-coupons` → 喜好推荐落地到可下单方案
- `query-lottery-info` / `draw-lottery` / `query-my-prizes` → 积分抽奖助手

## 安全说明

- 仓库内不保存真实 Token；仅使用环境变量 `MCD_MCP_TOKEN`
- 提供 `--mock` 离线演示，方便无 Token 体验与 CI
