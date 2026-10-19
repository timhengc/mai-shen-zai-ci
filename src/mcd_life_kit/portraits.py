"""年报、名片和头像共用已确认的等级人物素材。"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path


def portrait_path(identity: dict, override: Path | None = None) -> Path:
    if override is not None:
        return override
    gender = identity['gender']
    if gender not in {'male', 'female'}:
        raise ValueError('人物性别仅支持 male / female。')
    folder = Path(__file__).resolve().parents[2] / 'assets' / 'characters' / f'{gender}-v1'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    return folder / next(row['file'] for row in manifest['images'] if row['level'] == identity['level'])


def portrait_html(identity: dict, nickname: str | None = None, image: Path | None = None) -> str:
    image = portrait_path(identity, image)
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(image.suffix.lower())
    if mime is None:
        raise ValueError('人物图片请使用 PNG / JPEG / WebP。')
    encoded = base64.b64encode(image.read_bytes()).decode('ascii')
    label = html.escape(((nickname + '的') if nickname else '') + identity['title'] + '人物画像', quote=True)
    return f'<img class="character-image" src="data:{mime};base64,{encoded}" alt="{label}">'
