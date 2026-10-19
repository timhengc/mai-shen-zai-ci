# MCP 集成说明

## 实际业务

本项目是麦门身份视觉工坊：用真实可见订单生成统一门派身份，再制作年报、名片、代码头像。全部核心视觉在本地用代码绘制。模型仅作为用户明确选择的头像增强扩展，不参与身份计算。

- Server：`https://mcp.mcd.cn`
- Streamable HTTP + JSON-RPC 2.0；`Authorization: Bearer <环境变量中的 Token>`
- 配置示例：[mcp-config.example.json](mcp-config.example.json)
- 实际业务工具：**`order-list`**，只读查询历史订单。

`query-my-account` 在开发中仅验证过返回字段：它提供积分信息，没有性别字段；产品生成流程不调用它。当前没有已确认可用的本人性别查询工具。联系人信息不等同于本人档案，因此不查询配送地址取性别；缺失时由 Skill 询问可选称谓，跳过默认为男性。

## 调用流程

1. 首次缺少 Token 时，Agent 先展示官方入口二维码、链接与申请教程，用户可将 Token 发到当前对话或写入 `.env`；已有配置时跳过重复登录。完成连接后再处理功能选择与可选性别。
2. 对话 Token 通过 `--token-stdin` 单次使用、不回显、不自动保存；也可从环境变量或 `.env` / `mcd-token.env` 读取 `MCD_MCP_TOKEN`。`tools/list` 读取 `order-list` 的实时 inputSchema，再调用 `tools/call`。
3. 当前真实联调的 Schema 为 `{"properties": {}, "type": "object"}`，因此参数为 `{}`。接口未来支持分页时按实际 Schema 翻页，重复页或达到上限提示停止。不发明年份或分页参数。
4. 解析 `success/code/data.list`。工具或业务失败则终止，不伪造报告或替换成示例。
5. 按 `orderId` 去重、北京时间归年，只统计 `orderStatus` 明确已完成的订单；未知数字状态不猜测。
6. `orderProductList` 含 `comboItemList` 时拆成单品，乘以套餐份数，不重复计算父套餐。`realTotalAmount` 按元使用 Decimal 统计；只有明确的分字段才换算，缺失金额不当零。
7. 聚合完成订单数、活跃月份、全部已知单品种类（不是前五名）与门派关键词份数。[identity.py](src/mcd_life_kit/identity.py) 按 [预设规则](src/mcd_life_kit/identity_rules.json) 得到唯一身份。金额与性别不参与等级。v2.1 使用 `完成订单数×2 + min(月份数,12) + min(单品种类,12)`；同日多单分别计分，订单贡献不封顶，活跃日仅展示。最高等级门槛为160分，男女统一称“麦门真神”；9笔订单的示例36分仍属于扫地僧。
8. `all` 使用同一次查询、同一个身份和规则版本生成三件套；不让模型另行判定身份。SVG/CSS 角色与纹章依身份确定，Playwright/Chrome 导出 PNG。
9. 输出脱敏汇总与作品至 Git 忽略的 `out/`；不保存原始订单，不输出 Token、账号 ID、订单 ID、门店、地址或电话。

## 业务价值与边界

真实消费记忆转成可解释、可保存的视觉身份。没有金额门槛；等级只是虚构世界观设定，不是官方会员级别或现实评价。

**近期订单不代表完整年度记录。** 年份只用于本地筛选，不能突破服务端历史范围。产物标注本次可见订单、实际起止日期和已知金额/明细覆盖情况，不推算人群排名或补造缺失记录。

核心生成只读查询订单，不调用交易或账户修改能力。AI 头像仅生成可选简报；由 Agent 在用户选择后调用可用生图工具，传入角色设定与代码参考，不传原始个人数据或凭证。离线示例为 `examples/mock/orders.json` 的合成数据，产物显著标记示例。

## 登录授权能力核查

官方文档与随 Skill 附带的用户教程指引用户在官网完成登录 → 控制台激活 → 同意协议 → 复制 MCP Token；实时登录方式以官网当前页面为准。目前未找到公开 OAuth、设备码登录、扫码回调或自动获取 MCP Token 的开发者流程；核查 `https://mcp.mcd.cn/.well-known/oauth-protected-resource` 与 `/.well-known/oauth-authorization-server` 均返回404。这只是本次可确认的公开能力边界，不代表平台内部没有其他登录实现。

因此官方页面二维码可作为入口，不能冒充可自动回填凭证的授权二维码。当前先展示随 Skill 提供的二维码、官网链接和教程；用户可将 Token 发到 Agent 对话框供本次使用，或写入本地环境变量 / `.env`。教程页可离线生成 `mcd-token.env` 下载（放入项目根目录自动读取，已被 Git 忽略），不发送输入到网络。参考：[官方接入指南](https://github.com/M-China/mcd-mcp-server#1-申请-mcp-token)。
