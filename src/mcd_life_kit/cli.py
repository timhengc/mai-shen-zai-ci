"""麦门视觉工坊：首次连接引导、功能选择与视觉生成。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(_ROOT / 'src'))

from mcd_life_kit.annual_report import CST, artifact_stem, collect_orders, generate_report, load_env, records, summarize
from mcd_life_kit.identity import make_identity
from mcd_life_kit.mcp_client import DEFAULT_ENDPOINT, MCPClient, MCPError, read_token_file
from mcd_life_kit.profile import choose_display_name, fetch_account_name
from mcd_life_kit.visuals import generate_visual
from mcd_life_kit.onboarding import read_session_token, show_setup

MENU = '''麦门封神榜
你在麦门算老几？领取你的麦门专属身份

请选择要制作的内容：
  1. 麦门年报（annual-report）：真实订单回顾 + 最终门派身份
  2. 麦门名片（identity-card）：昵称、门派、境界和身份纹章
  3. 专属头像（avatar）：直接输出同一等级人物 PNG；可选 AI 创作简报
  4. 全套视觉（all）：同一数据快照生成以上三件套
选择功能后，请提供可选的性别称谓：男 / 女；跳过默认男。
示例：PYTHONPATH=src python3 -m mcd_life_kit.cli all --gender male
'''


def cmd_visual(args: argparse.Namespace) -> int:
    if not 2000 <= args.year <= datetime.now(CST).year:
        raise ValueError('年份应在 2000 与当前年份之间。')
    if not 1 <= args.max_pages <= 100:
        raise ValueError('--max-pages 应为 1 至 100。')
    artifact_stem('report', args.file_suffix)
    warnings = []
    fetched_name = None
    if args.mock:
        if args.token_stdin or args.env_file:
            raise ValueError('示例模式无需 Token，请移除凭证输入参数。')
        payload = json.loads(Path(args.mock_data or _ROOT / 'examples/mock/orders.json').read_text(encoding='utf-8'))
        orders, _ = records(payload)
    else:
        if args.env_file and args.token_stdin:
            raise ValueError('--env-file 与 --token-stdin 不能同时使用。')
        if args.env_file:
            client = MCPClient(token=read_token_file(Path(args.env_file)), endpoint=DEFAULT_ENDPOINT)
        else:
            load_env()
            client = MCPClient(token=read_session_token() if args.token_stdin else None)
        if not client.token:
            show_setup()
            return 2
        extra = json.loads(args.mcp_args)
        if not isinstance(extra, dict):
            raise ValueError('--mcp-args 必须是 JSON 对象。')
        try:
            available = client.list_tools()
            if args.nickname is None:
                fetched_name = fetch_account_name(client, available)
            orders, warnings = collect_orders(client, extra, args.max_pages, available_tools=available)
        except MCPError as exc:
            raise MCPError(str(exc).replace(client.token, '[Token 已隐藏]')) from None
    report = summarize(orders, args.year, demo=args.mock, warnings=warnings)
    report['identity'] = make_identity(report, args.gender)
    display_name, name_source = choose_display_name(args.nickname, fetched_name, args.nickname_fallback)
    report['display_name'], report['display_name_source'] = display_name, name_source
    output = Path(args.output or f'out/{args.command if args.command != "all" else "maimen"}')
    output.mkdir(parents=True, exist_ok=True)
    (output / f'{artifact_stem("identity",args.file_suffix)}.json').write_text(json.dumps(report['identity'], ensure_ascii=False, indent=2), encoding='utf-8')
    (output / f'{artifact_stem("report-data",args.file_suffix)}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    kinds = ['annual-report', 'identity-card', 'avatar'] if args.command == 'all' else [args.command]
    for kind in kinds:
        image = Path(args.portrait_image) if args.portrait_image else None
        if kind == 'annual-report':
            paths = generate_report(report, output, display_name, png=not args.html_only, file_suffix=args.file_suffix, portrait_image=image)
        else:
            paths = generate_visual(report, output, display_name, kind, png=not args.html_only, ai_brief=args.ai_avatar_brief, portrait_image=image, file_suffix=args.file_suffix)
        for path in paths:
            if path:
                print(path.resolve())
    print(f"{'合成示例' if args.mock else '真实 MCP'} · {report['year']} 年可见完成订单 {report['count']} 笔")
    print(f"最终身份：{report['identity']['sect']} · {report['identity']['title']}（{report['identity']['realm']}）")
    print(f"称谓来源：{report['identity']['gender_source']}；本次阅历 {report['identity']['score']} 分；近期记录不代表全年。")
    print(f"用户名：{display_name or '不显示'}（{name_source}）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='mcd-life-kit', description='麦门封神榜 · 你在麦门算老几？领取你的麦门专属身份')
    sub = parser.add_subparsers(dest='command')
    setup = sub.add_parser('setup', help='展示官方入口二维码、链接和 Token 申请教程')
    setup.add_argument('--output', default=str(_ROOT / 'out/setup'))
    setup.set_defaults(func=cmd_setup)
    for name, desc in [('annual-report', '麦门年报'), ('identity-card', '麦门名片'), ('avatar', '专属头像'), ('all', '同一快照的视觉三件套')]:
        command = sub.add_parser(name, help=desc)
        command.add_argument('--year', type=int, default=datetime.now(CST).year)
        command.add_argument('--nickname', default=None, help='明确指定显示名；默认取接口账号名，未返回则不显示')
        command.add_argument('--nickname-fallback', default=None, help='仅在接口未返回账号名时使用的备用显示名')
        command.add_argument('--env-file', default=None, help='仅使用指定账号文件的 Token，不回退到其他配置')
        command.add_argument('--file-suffix', default='', help='输出文件名后缀，例如 dhp → annual-report_dhp.html')
        command.add_argument('--gender', choices=['male', 'female'], default=None, help='可选称谓，省略默认为男；不代表真实外貌')
        command.add_argument('--mock', action='store_true', help='合成示例，不是个人真实记录')
        command.add_argument('--token-stdin', action='store_true', help='从隐藏终端输入或标准输入读取 Token，仅本次使用，不自动保存')
        command.add_argument('--mock-data', default=None)
        command.add_argument('--output', default=None, help='默认 out/<功能名>；全套默认 out/maimen')
        command.add_argument('--html-only', action='store_true', help='跳过页面截图，无需 Node.js；头像仍直接复制原始人物图片')
        command.add_argument('--max-pages', type=int, default=30)
        command.add_argument('--mcp-args', default='{}')
        command.add_argument('--portrait-image', default=None, help='覆盖自动选图；年报、名片、头像共用指定的本地 PNG/JPEG/WebP')
        if name in {'avatar', 'all'}:
            command.add_argument('--ai-avatar-brief', action='store_true', help='额外输出生图简报，不自动调用或假装完成模型生图')
        else:
            command.set_defaults(ai_avatar_brief=False)
        command.set_defaults(func=cmd_visual)
    return parser


def cmd_setup(args: argparse.Namespace) -> int:
    show_setup(Path(args.output))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command is None:
            load_env()
            if not MCPClient().token:
                show_setup()
            else:
                print(MENU)
            return 0
        return int(args.func(args))
    except (MCPError, ValueError, OSError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
