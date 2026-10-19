"""首次连接引导：静态官方入口二维码、教程与本地配置，不模拟授权回调。"""
from __future__ import annotations

import base64
import getpass
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "onboarding"
OFFICIAL_URL = "https://open.mcd.cn/mcp"


def read_session_token() -> str:
    """交互终端关闭输入回显；管道读 stdin，均不自动落盘。"""
    value = getpass.getpass("MCP Token（不回显，仅本次使用）：") if sys.stdin.isatty() else sys.stdin.read()
    token = value.strip()
    if not token or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in token):
        raise ValueError("Token 应为非空单行字符串，请只粘贴复制的 Token。")
    return token


def generate_setup(output: Path) -> Path:
    template = (Path(__file__).parent / "templates" / "setup.html").read_text(encoding="utf-8")
    images = {"__QR_IMAGE__": "official-platform-qr.png", "__GUIDE_IMAGE__": "token-guide.png"}
    values = {key: "data:image/png;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")
              for key, name in images.items()}
    result = re.sub("|".join(map(re.escape, values)), lambda match: values[match[0]], template)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "index.html"
    path.write_text(result, encoding="utf-8")
    return path


def show_setup(output: Path = ROOT / "out" / "setup") -> Path:
    path = generate_setup(output)
    print("首次使用：先连接麦当劳 MCP")
    print(f"官方登录入口 / 接入文档：{OFFICIAL_URL}")
    print(f"入口二维码：{(ASSETS / 'official-platform-qr.png').resolve()}")
    print(f"申请教程图：{(ASSETS / 'token-guide.png').resolve()}")
    print(f"可直接打开的登录教程：{path.resolve()}")
    print("打开官网 → 按页面提示完成登录 → 控制台激活并同意协议 → 复制 Token。")
    print("复制后可直接发到 Agent 对话框（默认仅本次使用），或写入项目 .env：MCD_MCP_TOKEN=你的Token；教程页也可下载 mcd-token.env 放到项目根目录。")
    print("入口二维码打开官网；完成配置后，再选择年报 / 名片 / 头像 / 全套视觉。")
    return path
