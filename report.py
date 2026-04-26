from __future__ import annotations
import csv
import io
from models import Property, PropertyType, RenovationEstimate, Score


def _bar(score: float, max_score: float = 20, width: int = 10) -> str:
    filled = round(score / max_score * width)
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def _fmt_man(value: float) -> str:
    return f"{value:,.0f}万円"


def _strategy_table(
    properties: list[Property],
    estimates: dict[str, RenovationEstimate],
    scores: dict[str, Score],
) -> str:
    groups: dict[str, list] = {}
    for p in properties:
        label = p.property_type.value
        if label not in groups:
            groups[label] = []
        groups[label].append(p)

    lines = [
        "## 戦略別比較",
        "",
        "| 戦略 | 件数 | 平均総費用 | 平均スコア | 平均月額返済 |",
        "|------|------|-----------|-----------|-------------|",
    ]
    for label, props in groups.items():
        avg_cost = sum(estimates[p.id].total_cost_man for p in props) / len(props)
        avg_score = sum(scores[p.id].total for p in props) / len(props)
        avg_monthly = sum(estimates[p.id].monthly_payment_yen for p in props) / len(props)
        lines.append(
            f"| {label} | {len(props)} | {_fmt_man(avg_cost)} "
            f"| {avg_score:.1f} | {avg_monthly:,.0f}円 |"
        )
    return "\n".join(lines)


def _property_card(
    rank: int, p: Property, est: RenovationEstimate, sc: Score
) -> str:
    badge = {"Recommended": "✅ 推奨", "Consider": "🔶 検討", "Skip": "❌ 非推奨"}.get(
        sc.recommendation, sc.recommendation
    )
    lines = [
        f"### {rank}. {p.name}  {badge}",
        "",
        f"**総合スコア: {sc.total}/100**",
        "",
        "| 項目 | スコア | バー |",
        "|------|--------|------|",
        f"| 広さ | {sc.size_score}/20 | {_bar(sc.size_score)} |",
        f"| 立地 | {sc.location_score}/20 | {_bar(sc.location_score)} |",
        f"| 状態 | {sc.condition_score}/20 | {_bar(sc.condition_score)} |",
        f"| ライフスタイル | {sc.lifestyle_score}/20 | {_bar(sc.lifestyle_score)} |",
        f"| 価値 | {sc.value_score}/20 | {_bar(sc.value_score)} |",
        "",
        "**費用内訳**",
        "",
        "| 項目 | 金額 |",
        "|------|------|",
        f"| 購入価格 | {_fmt_man(p.price_man)} |",
    ]

    if est.total_renovation_man > 0:
        lines.append(f"| リノベーション合計 | {_fmt_man(est.total_renovation_man)} |")
    if est.construction_man > 0:
        lines.append(f"| 新築工事費 | {_fmt_man(est.construction_man)} |")

    lines += [
        f"| 諸費用 | {_fmt_man(est.acquisition_costs_man)} |",
        f"| **総費用** | **{_fmt_man(est.total_cost_man)}** |",
        f"| 月額返済 (35年) | {est.monthly_payment_yen:,}円 |",
        "",
        f"**物件概要:** {p.district.value} / "
        f"土地{p.land_tsubo:.0f}坪 / 建物{p.building_tsubo:.0f}坪 / "
        f"築{p.age_years}年 / 駅{p.station_minutes}分",
    ]

    if p.notes:
        lines.append(f"\n> {p.notes}")

    return "\n".join(lines)


def _renovation_detail(
    properties: list[Property], estimates: dict[str, RenovationEstimate]
) -> str:
    used = [p for p in properties if p.property_type == PropertyType.USED_HOUSE]
    if not used:
        return ""

    lines = ["## リノベーション詳細 (中古一戸建て)", ""]
    for p in used:
        est = estimates[p.id]
        lines += [
            f"### {p.name}",
            "",
            "| 工事区分 | 金額 |",
            "|----------|------|",
            f"| 基礎・躯体 | {_fmt_man(est.base_renovation_man)} |",
            f"| 内装 | {_fmt_man(est.interior_renovation_man)} |",
            f"| 外装（雪荷重対応） | {_fmt_man(est.exterior_renovation_man)} |",
            f"| **合計** | **{_fmt_man(est.total_renovation_man)}** |",
            "",
        ]
    return "\n".join(lines)


def generate_markdown(
    properties: list[Property],
    estimates: dict[str, RenovationEstimate],
    scores: dict[str, Score],
) -> str:
    sorted_props = sorted(properties, key=lambda p: scores[p.id].total, reverse=True)
    top = scores[sorted_props[0].id] if sorted_props else None

    sections = [
        "# 物件分析レポート",
        "",
        "## エグゼクティブサマリー",
        "",
        f"- 分析物件数: **{len(properties)}件**",
    ]

    if top:
        top_p = next(p for p in properties if p.id == top.property_id)
        sections += [
            f"- 最高スコア: **{top_p.name}** ({top.total}/100 — {top.recommendation})",
        ]

    budget_range = (
        min(e.total_cost_man for e in estimates.values()),
        max(e.total_cost_man for e in estimates.values()),
    )
    sections.append(
        f"- 費用レンジ: {_fmt_man(budget_range[0])} 〜 {_fmt_man(budget_range[1])}"
    )

    sections += [
        "",
        _strategy_table(properties, estimates, scores),
        "",
        "## 物件別評価",
        "",
    ]

    for rank, p in enumerate(sorted_props, 1):
        sections.append(_property_card(rank, p, estimates[p.id], scores[p.id]))
        sections.append("")

    detail = _renovation_detail(sorted_props, estimates)
    if detail:
        sections += [detail, ""]

    return "\n".join(sections)


def generate_csv(
    properties: list[Property],
    estimates: dict[str, RenovationEstimate],
    scores: dict[str, Score],
) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "name", "type", "district", "price_man", "land_tsubo",
        "building_tsubo", "age_years", "condition", "station_minutes",
        "total_cost_man", "monthly_payment_yen", "score", "recommendation",
    ])
    for p in sorted(properties, key=lambda x: scores[x.id].total, reverse=True):
        est = estimates[p.id]
        sc = scores[p.id]
        writer.writerow([
            p.id, p.name, p.property_type.value, p.district.value,
            p.price_man, p.land_tsubo, p.building_tsubo, p.age_years,
            p.condition.value, p.station_minutes,
            round(est.total_cost_man, 1), est.monthly_payment_yen,
            sc.total, sc.recommendation,
        ])
    return buf.getvalue()
