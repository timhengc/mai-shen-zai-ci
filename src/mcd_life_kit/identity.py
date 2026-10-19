"""麦门身份规则：同一数据快照为所有视觉产物提供唯一身份。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RULES = json.loads((Path(__file__).parent / "identity_rules.json").read_text(encoding="utf-8"))


def resolve_gender(gender: str | None = None, account_profile: dict | None = None) -> tuple[str, str]:
    """只接受明确字段，未知数字枚举不推断；联系人信息不作为账号性别。"""
    aliases = {"male": "male", "男": "male", "男性": "male", "female": "female", "女": "female", "女性": "female"}
    if gender is not None:
        if gender not in aliases:
            raise ValueError("性别称谓应为 male / female；未指定时默认 male。")
        return aliases[gender], "user"
    if account_profile:
        for key in ("gender", "sex"):
            value = account_profile.get(key)
            if isinstance(value, str) and value.lower() in aliases:
                return aliases[value.lower()], "account"
    return "male", "default"


def make_identity(report: dict, gender: str | None = None, account_profile: dict | None = None) -> dict:
    chosen, source = resolve_gender(gender, account_profile)
    orders = max(int(report["count"]), 0)
    months = min(sum(n > 0 for n in report["months"]), 12)
    kinds = min(max(int(report["unique_foods"]), 0), 12)
    components = {"orders": orders * 2, "months": months, "variety": kinds}
    score = sum(components.values())
    tier = next(t for t in reversed(RULES["tiers"]) if score >= t["minimum"])
    # 只采用已知单品；同分按预设门派顺序，所有产物共享同一个判定结果。
    sect_scores = {s["key"]: report.get("taste_scores", {}).get(s["key"], 0) for s in RULES["sects"]}
    sect = max(RULES["sects"], key=lambda s: sect_scores[s["key"]])
    if not any(sect_scores.values()):
        sect = RULES["fallback_sect"]
    title = tier["titles"][chosen]
    canonical = {"rules_version": RULES["version"], "year": report["year"], "count": report["count"], "days": report["days"],
                 "months": report["months"], "unique_foods": report["unique_foods"], "taste_scores": sect_scores,
                 "gender": chosen, "demo": report["demo"]}
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:8].upper()
    return {"rules_version": RULES["version"], "level": tier["level"], "realm": tier["realm"], "title": title,
            "sect": sect["name"], "sect_key": sect["key"], "symbol": sect["symbol"], "motto": sect["motto"],
            "score": score, "score_components": components, "gender": chosen, "gender_source": source,
            "serial": f"MK-{report['year']}-{digest}", "scope": "本次可见订单推演 · 虚构门派身份",
            "basis": f"{orders} 笔完成订单 · {months} 个有记录月份 · {report['unique_foods']} 种已知餐品",
            "formula": "完成订单数×2 + min(有记录月份,12) + min(餐品种类,12)；同日多单均计入，订单分不封顶，不使用消费金额。"}


def taste_scores(foods: dict[str, int]) -> dict[str, int]:
    scores = {sect["key"]: 0 for sect in RULES["sects"]}
    for name, quantity in foods.items():
        for sect in RULES["sects"]:
            if any(word in name for word in sect["keywords"]):
                scores[sect["key"]] += quantity
                break
    return scores
