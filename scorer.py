from __future__ import annotations
from models import Property, Condition, District, Score
from costs import RenovationEstimate

TARGET_DISTRICTS = {District.NISHI, District.KITA, District.TEINE}

_CONDITION_PTS = {
    Condition.EXCELLENT: 10,
    Condition.GOOD: 8,
    Condition.FAIR: 5,
    Condition.POOR: 2,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score_property(p: Property, est: RenovationEstimate) -> Score:
    # Size score (0-20)
    land_pts = _clamp((p.land_tsubo / 150) * 10, 0, 10)
    bldg_pts = _clamp((p.building_tsubo / 50) * 10, 0, 10)
    size_score = land_pts + bldg_pts

    # Location score (0-20)
    station_pts = _clamp((30 - p.station_minutes) / 30 * 10, 0, 10)
    district_pts = 10.0 if p.district in TARGET_DISTRICTS else 5.0
    location_score = station_pts + district_pts

    # Condition score (0-20)
    age_pts = _clamp((40 - p.age_years) / 40 * 10, 0, 10)
    cond_pts = float(_CONDITION_PTS[p.condition])
    condition_score = age_pts + cond_pts

    # Lifestyle score (0-20)
    outdoor_pts = 10.0 if p.has_outdoor_space else 0.0
    school_pts = float(p.school_district_rating * 2)  # 1-5 → 2-10
    lifestyle_score = outdoor_pts + school_pts

    # Value score (0-20): lower cost-per-tsubo is better
    cost_per_tsubo = est.total_cost_man / p.land_tsubo if p.land_tsubo > 0 else 999
    value_score = _clamp((80 - cost_per_tsubo) / 80 * 20, 0, 20)

    total = size_score + location_score + condition_score + lifestyle_score + value_score

    if total >= 70:
        recommendation = "Recommended"
    elif total >= 50:
        recommendation = "Consider"
    else:
        recommendation = "Skip"

    return Score(
        property_id=p.id,
        total=round(total, 1),
        size_score=round(size_score, 1),
        location_score=round(location_score, 1),
        condition_score=round(condition_score, 1),
        lifestyle_score=round(lifestyle_score, 1),
        value_score=round(value_score, 1),
        recommendation=recommendation,
    )
