"""共用预置人物图生成视觉产物；模型增强只输出可选创作简报。"""
from __future__ import annotations

import html
import json
import re
import subprocess
import shutil
from pathlib import Path

from .annual_report import ROOT, artifact_stem
from .mcp_client import MCPError
from .portraits import portrait_html, portrait_path


def render_visual(report: dict, nickname: str | None, kind: str, png: bool = True, portrait_image: Path | None = None, file_suffix: str = "") -> str:
    identity = report["identity"]
    image = portrait_path(identity, portrait_image)
    image_extension = image.suffix.lower() if kind == 'avatar' else '.png'
    template = (Path(__file__).parent / 'templates' / 'identity.html').read_text(encoding='utf-8')
    values = {"TITLE": '麦门名片' if kind == 'identity-card' else '专属头像', "KIND": kind,
              "NICKNAME": nickname or "", "NICKNAME_HIDDEN": '' if nickname else 'hidden', "SECT": identity['sect'], "IDENTITY": identity['title'],
              "REALM": identity['realm'], "LEVEL": f"{identity['level']:02d}", "MOTTO": identity['motto'],
              "SERIAL": identity['serial'], "BASIS": identity['basis'], "SCORE": str(identity['score']),
              "SCOPE": identity['scope'], "YEAR": str(report['year']), "RULE": identity['formula'],
              "DEMO": '合成示例 · 非真实身份数据' if report['demo'] else '真实 MCP 数据 · 虚构门派设定',
              "PNG": f'{artifact_stem(kind, file_suffix)}{image_extension}' if png or kind == 'avatar' else '', "PORTRAIT_CLASS": 'custom-image'}
    replacements = {key: html.escape(value, quote=True) for key, value in values.items()}
    portrait = portrait_html(identity, nickname, image)
    replacements['CARD_AVATAR'] = portrait if kind == 'identity-card' else ''
    replacements['STANDALONE_AVATAR'] = portrait if kind == 'avatar' else ''
    return re.sub(r'__([A-Z_]+)__', lambda match: replacements[match[1]], template)


def generate_visual(report: dict, output: Path, nickname: str | None, kind: str, png: bool = True, ai_brief: bool = False, portrait_image: Path | None = None, file_suffix: str = "") -> tuple[Path, Path | None]:
    output.mkdir(parents=True, exist_ok=True)
    stem = artifact_stem(kind, file_suffix)
    html_path, png_path = output / f'{stem}.html', output / f'{stem}.png'
    html_path.write_text(render_visual(report, nickname, kind, png, portrait_image, file_suffix), encoding='utf-8')
    (output / f'{artifact_stem("identity", file_suffix)}.json').write_text(json.dumps(report['identity'], ensure_ascii=False, indent=2), encoding='utf-8')
    if kind == 'avatar':
        image = portrait_path(report['identity'], portrait_image)
        png_path = output / f'{stem}{image.suffix.lower()}'
        if image.resolve() != png_path.resolve():
            shutil.copyfile(image, png_path)
        # 清理旧版程序在同一输出目录生成的代码头像。
        (output / f'{stem}.svg').unlink(missing_ok=True)
        if ai_brief:
            (output / f'{artifact_stem("avatar-ai-brief", file_suffix)}.md').write_text(avatar_brief(report['identity']), encoding='utf-8')
        return html_path, png_path
    if png:
        try:
            subprocess.run(['node', str(ROOT / 'scripts/export-report.cjs'), str(html_path.resolve()), str(png_path.resolve())], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise MCPError(f'HTML 已保存至 {html_path}；PNG 导出失败，请运行 npm ci 并安装 Chrome/Chromium。') from exc
    return html_path, png_path if png else None


def avatar_brief(identity: dict) -> str:
    return f'''# 可选头像生图简报

此文件是创作提示词，没有执行模型生图；默认预置人物头像已经可以使用。
仅在用户明确选择 AI 增强头像后，将下述设定交给当前 Agent 可用的生图工具。没有工具时保留预置头像并说明，不声称已生成。

为原创虚构「{identity['sect']}」角色创作一张正方形头像，身份「{identity['title']}」，境界「{identity['realm']}」。
以输出的 avatar.png 人物图为视觉参考，保留赤红、金黄和奶油白配色、居中半身构图、友善表情。
角色称谓偏好：{identity['gender']}。不推断用户真实外貌；不需要真人照片，不包含昵称、账单或订单编号。
采用简约二维涂鸦风格：粗黑线、扁平红黄色块、圆方脸、憨厚可爱且呆萌，五官与耳朵采用原创设计。若用户提供已确认的人物图，优先保持该角色一致性。
衣服胸前必须有一个小巧的金黄色麦当劳双拱门 M 标志，约为躯干衣服宽度的5%—7%，像普通衣服的小刺绣品牌标，不要大面积胸前印花。除此之外不添加文字或其他品牌标志。
不做 OK 手势；扫地僧双手自然握扫帚。全身版保持与半身版一致的脸型、五官、耳朵、服装与小胸标。
'''
