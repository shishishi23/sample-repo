#!/usr/bin/env python3
"""Property renovation analysis CLI for Sapporo-area real estate."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from costs import estimate_costs
from models import Property, RenovationEstimate, Score
from report import generate_csv, generate_markdown
from scorer import score_property


def load_properties(path: Path) -> list[Property]:
    if path.suffix.lower() == ".csv":
        return _load_csv(path)
    return _load_json(path)


def _load_json(path: Path) -> list[Property]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [Property.from_dict(d) for d in data]


def _load_csv(path: Path) -> list[Property]:
    properties = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            row["has_outdoor_space"] = row["has_outdoor_space"].lower() in ("1", "true", "yes")
            row["school_district_rating"] = int(row["school_district_rating"])
            properties.append(Property.from_dict(row))
    return properties


def _apply_filters(
    properties: list[Property],
    budget: float | None,
    min_land: float,
    min_building: float,
    estimates: dict[str, RenovationEstimate],
) -> list[Property]:
    result = []
    for p in properties:
        if p.land_tsubo < min_land:
            continue
        if p.building_tsubo < min_building:
            continue
        if budget is not None and estimates[p.id].total_cost_man > budget:
            continue
        result.append(p)
    return result


def _sort_key(p: Property, estimates: dict, scores: dict, sort_by: str):
    if sort_by == "cost":
        return estimates[p.id].total_cost_man
    if sort_by == "value":
        return -(scores[p.id].value_score)
    return -(scores[p.id].total)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="札幌エリア物件リノベーション分析ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="物件データ (JSON or CSV)")
    parser.add_argument("-o", "--output", type=Path, default=None, help="出力ファイル (省略時: stdout)")
    parser.add_argument(
        "-f", "--format", choices=["markdown", "csv"], default="markdown", help="出力形式"
    )
    parser.add_argument("--budget", type=float, default=None, metavar="MAX", help="予算上限 (万円)")
    parser.add_argument("--min-land", type=float, default=150, metavar="TSUBO", help="最低土地面積 (坪)")
    parser.add_argument("--min-building", type=float, default=50, metavar="TSUBO", help="最低建物面積 (坪)")
    parser.add_argument(
        "--sort", choices=["score", "cost", "value"], default="score", help="並び順"
    )
    parser.add_argument("--top", type=int, default=None, metavar="N", help="上位N件のみ表示")
    parser.add_argument("--compare", nargs="+", metavar="ID", help="特定物件IDを詳細比較")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: ファイルが見つかりません: {args.input}", file=sys.stderr)
        sys.exit(1)

    all_props = load_properties(args.input)
    if not all_props:
        print("Error: 物件データが空です", file=sys.stderr)
        sys.exit(1)

    # Calculate costs and scores for all properties first (needed for budget filter)
    all_estimates: dict[str, RenovationEstimate] = {p.id: estimate_costs(p) for p in all_props}
    all_scores: dict[str, Score] = {
        p.id: score_property(p, all_estimates[p.id]) for p in all_props
    }

    # Apply filters
    if args.compare:
        properties = [p for p in all_props if p.id in args.compare]
    else:
        properties = _apply_filters(
            all_props, args.budget, args.min_land, args.min_building, all_estimates
        )

    if not properties:
        print("条件に合致する物件が見つかりませんでした。フィルター条件を緩めてください。", file=sys.stderr)
        sys.exit(0)

    estimates = {p.id: all_estimates[p.id] for p in properties}
    scores = {p.id: all_scores[p.id] for p in properties}

    # Sort
    properties.sort(key=lambda p: _sort_key(p, estimates, scores, args.sort))
    if args.sort == "cost":
        pass  # ascending for cost
    else:
        pass  # already descending via negative in _sort_key

    if args.top:
        properties = properties[: args.top]
        estimates = {p.id: estimates[p.id] for p in properties}
        scores = {p.id: scores[p.id] for p in properties}

    if args.format == "csv":
        output = generate_csv(properties, estimates, scores)
    else:
        output = generate_markdown(properties, estimates, scores)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"レポートを書き込みました: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
