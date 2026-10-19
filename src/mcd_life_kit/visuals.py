"""纯 SVG/CSS 视觉产物；头像的模型增强只输出可选创作简报。"""
from __future__ import annotations

import hashlib
import base64
import html
import json
import math
import re
import subprocess
from pathlib import Path

from .annual_report import ROOT, artifact_stem
from .mcp_client import MCPError


def avatar_svg(identity: dict, nickname: str | None) -> str:
    """同一身份、昵称得到相同的角色；无需图片素材、网络或生图服务。"""
    esc = html.escape
    nickname = nickname or ""
    level = identity["level"]
    seed = int(hashlib.sha256((identity["serial"] + nickname).encode()).hexdigest()[:8], 16)
    stars = []
    for i in range(12 + level * 2):
        angle = (i * 137.508 + seed % 360) * math.pi / 180
        radius = 205 + (i % 4) * 12
        x, y = 300 + math.cos(angle) * radius, 290 + math.sin(angle) * radius
        stars.append(f'<path d="M{x-3:.1f} {y:.1f}h6m-3 -3v6" stroke="#ffd45a" stroke-width="2" opacity=".65"/>')
    rings = ''.join(f'<circle cx="300" cy="268" r="{164+i*15}" fill="none" stroke="#ffcf25" stroke-opacity="{.4-i*.08}" stroke-width="1" stroke-dasharray="{3+i*3} 12"/>' for i in range(min(4, 1+level//2)))
    hair = '<path d="M213 230Q186 303 207 357L242 331L236 252M387 230Q414 303 393 357L358 331L364 252" fill="#391d1a"/>' if identity["gender"] == 'female' else ''
    cosmic = '<path d="M214 145L239 91L270 128L300 73L330 128L361 91L386 145Z" fill="url(#gold)" stroke="#ffe7a2" stroke-width="2"/>' if level >= 5 else '<path d="M258 154L270 113L300 95L330 113L342 154Z" fill="url(#gold)"/>'
    sect_art = {
        'bubble': '<g fill="#ffdf7e" fill-opacity=".1" stroke="#ffdf7e" stroke-width="2"><circle cx="443" cy="214" r="25"/><circle cx="466" cy="160" r="12"/><circle cx="459" cy="274" r="10"/></g>',
        'fries': '<g transform="translate(432 165) rotate(19)"><path d="M0 0L10 -18L20 0V163H0Z" fill="url(#gold)"/><path d="M-12 163H32M10 164V194" stroke="#ffdf7e" stroke-width="8" stroke-linecap="round"/></g>',
        'burger': '<g transform="translate(445 218)" fill="none" stroke="#ffdf7e" stroke-width="3"><path d="M-31 0Q-29 -36 0 -36Q29 -36 31 0Z"/><path d="M-32 10L-12 16L8 9L29 15M-31 25H31M-27 35Q0 49 27 35"/></g>',
        'coffee': '<g transform="translate(435 220)" fill="none" stroke="#ffdf7e" stroke-width="3"><path d="M-24 0H24V29Q24 47 0 47Q-24 47 -24 29ZM24 6Q57 8 26 31M-5 -12Q-17 -24 -3 -36M11 -14Q23 -26 9 -38"/></g>',
        'sweet': '<g transform="translate(446 225)" fill="#ffdf7e" fill-opacity=".15" stroke="#ffdf7e" stroke-width="2"><path d="M0 34C-65 -4 -24 -47 0 -18C24 -47 65 -4 0 34Z"/><path d="M0 34V88"/></g>',
        'chicken': '<g transform="translate(445 228) rotate(20)" fill="none" stroke="#ffdf7e" stroke-width="2"><path d="M0 63Q-44 -16 0 -66Q44 -16 0 63ZM0 55V-46M0 25L-17 8M0 3L18 -15M0 -17L-13 -31"/></g>',
    }.get(identity['sect_key'], '')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" role="img" aria-label="{esc((nickname+'的') if nickname else '')}{esc(identity['title'])}代码头像">
<title>{esc(identity['sect'])} · {esc(identity['title'])}</title>
<defs><radialGradient id="sky"><stop stop-color="#df3330"/><stop offset="1" stop-color="#6c121c"/></radialGradient><linearGradient id="gold" x2="0" y2="1"><stop stop-color="#fff0a6"/><stop offset=".5" stop-color="#ffcf25"/><stop offset="1" stop-color="#d99626"/></linearGradient><linearGradient id="robe" x2="1" y2="1"><stop stop-color="#f14b33"/><stop offset="1" stop-color="#9b1524"/></linearGradient></defs>
<rect width="600" height="600" rx="48" fill="url(#sky)"/>
<circle cx="300" cy="285" r="261" fill="none" stroke="#ffcf25" stroke-opacity=".3"/><circle cx="300" cy="285" r="252" fill="none" stroke="#ffcf25" stroke-opacity=".12"/>
{rings}{''.join(stars)}
<path d="M39 411Q112 369 154 414Q186 448 135 459H53M463 431Q499 393 549 418Q578 443 540 453" fill="none" stroke="#ffcd65" stroke-opacity=".25" stroke-width="3"/>
{sect_art}
<ellipse cx="300" cy="527" rx="162" ry="19" fill="#3d101c" opacity=".35"/>
<path d="M161 505L188 405Q215 358 269 351H331Q389 358 412 405L439 505Q300 552 161 505Z" fill="url(#robe)" stroke="#ffcf25" stroke-width="3"/>
<path d="M213 380L261 354L300 405L339 354L387 380L340 448H260Z" fill="url(#gold)"/>
<path d="M272 356L300 386L328 356V330H272Z" fill="#f6c18a"/>
{hair}<path d="M209 239Q202 157 267 150Q294 116 329 151Q401 149 391 239L367 288H233Z" fill="#391d1a"/>
{cosmic}<path d="M251 164Q300 144 349 164" stroke="#a64d31" stroke-width="10" fill="none"/>
<ellipse cx="218" cy="272" rx="16" ry="23" fill="#f4bf8e"/><ellipse cx="382" cy="272" rx="16" ry="23" fill="#f4bf8e"/>
<path d="M226 219Q256 229 281 195Q321 229 374 218L370 290Q361 344 300 351Q239 344 230 290Z" fill="#ffdbaf"/>
<path d="M251 259Q263 251 275 258M325 258Q337 251 349 259" stroke="#542b25" stroke-width="5" stroke-linecap="round" fill="none"/>
<path d="M258 277V285M342 277V285" stroke="#542b25" stroke-width="7" stroke-linecap="round"/>
<ellipse cx="248" cy="294" rx="14" ry="7" fill="#ef9b7e" opacity=".5"/><ellipse cx="352" cy="294" rx="14" ry="7" fill="#ef9b7e" opacity=".5"/>
<path d="M287 309Q300 321 313 309" stroke="#a44938" stroke-width="4" fill="none" stroke-linecap="round"/>
<path d="M264 402L300 435L336 402M300 435V515" stroke="#ffe8a1" stroke-width="3" fill="none"/>
<g data-brand="mcdonalds" aria-label="麦当劳金色双拱门标志" transform="translate(368 421) scale(.25)"><path d="M0 66C0 28 6 0 20 0C32 0 39 21 40 48C41 21 48 0 60 0C74 0 80 28 80 66H67C67 32 65 13 60 13C53 13 48 36 47 66H33C32 36 27 13 20 13C15 13 13 32 13 66Z" fill="#ffcf25"/></g>
<circle cx="300" cy="467" r="25" fill="#ffcf25" stroke="#fff0ae" stroke-width="3"/>
<text x="300" y="476" text-anchor="middle" fill="#95202a" font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="26" font-weight="800">{esc(identity['symbol'])}</text>
<path d="M190 453L230 472M410 453L370 472" stroke="#ffc35a" stroke-width="17" stroke-linecap="round"/>
<text x="300" y="574" text-anchor="middle" fill="#ffda72" font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="16" letter-spacing="5">{esc(identity['sect'])} · {esc(identity['realm'])}</text></svg>'''


def render_visual(report: dict, nickname: str | None, kind: str, png: bool = True, portrait_image: Path | None = None, file_suffix: str = "") -> str:
    identity = report["identity"]
    template = (Path(__file__).parent / 'templates' / 'identity.html').read_text(encoding='utf-8')
    values = {"TITLE": '麦门名片' if kind == 'identity-card' else '专属代码头像', "KIND": kind,
              "NICKNAME": nickname or "", "NICKNAME_HIDDEN": '' if nickname else 'hidden', "SECT": identity['sect'], "IDENTITY": identity['title'],
              "REALM": identity['realm'], "LEVEL": f"{identity['level']:02d}", "MOTTO": identity['motto'],
              "SERIAL": identity['serial'], "BASIS": identity['basis'], "SCORE": str(identity['score']),
              "SCOPE": identity['scope'], "YEAR": str(report['year']), "RULE": identity['formula'],
              "DEMO": '合成示例 · 非真实身份数据' if report['demo'] else '真实 MCP 数据 · 虚构门派设定',
              "PNG": f'{artifact_stem(kind, file_suffix)}.png' if png else '', "PORTRAIT_CLASS": 'custom-image' if portrait_image else ''}
    replacements = {key: html.escape(value, quote=True) for key, value in values.items()}
    svg = avatar_svg(identity, nickname)
    # 每页只保留可见的一个 SVG，避免重复渐变 ID 引用隐藏的 defs。
    replacements['CARD_AVATAR'] = svg if kind == 'identity-card' else ''
    replacements['STANDALONE_AVATAR'] = svg if kind == 'avatar' else ''
    if portrait_image:
        if kind != 'identity-card':
            raise ValueError('自定义人物图片目前用于麦门名片。')
        mime = {'.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp'}.get(portrait_image.suffix.lower())
        if not mime:
            raise ValueError('名片人物图片请使用 PNG / JPEG / WebP。')
        encoded = base64.b64encode(portrait_image.read_bytes()).decode('ascii')
        owner = (nickname + '的') if nickname else ''
        replacements['CARD_AVATAR'] = f'<img class="character-image" src="data:{mime};base64,{encoded}" alt="{html.escape(owner+identity["title"],quote=True)}人物画像">'
    return re.sub(r'__([A-Z_]+)__', lambda match: replacements[match[1]], template)


def generate_visual(report: dict, output: Path, nickname: str | None, kind: str, png: bool = True, ai_brief: bool = False, portrait_image: Path | None = None, file_suffix: str = "") -> tuple[Path, Path | None]:
    output.mkdir(parents=True, exist_ok=True)
    stem = artifact_stem(kind, file_suffix)
    html_path, png_path = output / f'{stem}.html', output / f'{stem}.png'
    html_path.write_text(render_visual(report, nickname, kind, png, portrait_image, file_suffix), encoding='utf-8')
    (output / f'{artifact_stem("identity", file_suffix)}.json').write_text(json.dumps(report['identity'], ensure_ascii=False, indent=2), encoding='utf-8')
    if kind == 'avatar':
        (output / f'{stem}.svg').write_text(avatar_svg(report['identity'], nickname), encoding='utf-8')
        if ai_brief:
            (output / f'{artifact_stem("avatar-ai-brief", file_suffix)}.md').write_text(avatar_brief(report['identity']), encoding='utf-8')
    if png:
        try:
            subprocess.run(['node', str(ROOT / 'scripts/export-report.cjs'), str(html_path.resolve()), str(png_path.resolve())], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise MCPError(f'HTML 已保存至 {html_path}；PNG 导出失败，请运行 npm ci 并安装 Chrome/Chromium。') from exc
    return html_path, png_path if png else None


def avatar_brief(identity: dict) -> str:
    return f'''# 可选头像生图简报

此文件是创作提示词，没有执行模型生图；默认代码头像已经可以使用。
仅在用户明确选择 AI 增强头像后，将下述设定交给当前 Agent 可用的生图工具。没有工具时保留代码头像并说明，不声称已生成。

为原创虚构「{identity['sect']}」角色创作一张正方形头像，身份「{identity['title']}」，境界「{identity['realm']}」。
以输出的 avatar.svg 为视觉参考，保留赤红、金黄和奶油白配色、门派纹章、居中半身构图、友善表情。
角色称谓偏好：{identity['gender']}。不推断用户真实外貌；不需要真人照片，不包含昵称、账单或订单编号。
采用简约二维涂鸦风格：粗黑线、扁平红黄色块、圆方脸、憨厚可爱且呆萌，五官与耳朵采用原创设计。若用户提供已确认的人物图，优先保持该角色一致性。
衣服胸前必须有一个小巧的金黄色麦当劳双拱门 M 标志，约为躯干衣服宽度的5%—7%，像普通衣服的小刺绣品牌标，不要大面积胸前印花。除此之外不添加文字或其他品牌标志。
不做 OK 手势；扫地僧双手自然握扫帚。全身版保持与半身版一致的脸型、五官、耳朵、服装与小胸标。
'''
