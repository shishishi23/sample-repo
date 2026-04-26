from __future__ import annotations
import math
from models import Property, PropertyType, Condition, RenovationEstimate

SAPPORO = {
    "snow_load_multiplier": 1.2,
    "new_build_rate_man_per_tsubo": 80,
    "acquisition_rate": 0.075,
    "mortgage_annual_rate": 0.01635,
    "mortgage_years": 35,
    "down_payment_rate": 0.10,
}

# Base renovation cost per building 坪 by age bracket (万円/坪)
_BASE_RENO_BY_AGE = [
    (10,  0),
    (20,  5),
    (30, 10),
    (999, 18),
]

_CONDITION_MULTIPLIER = {
    Condition.EXCELLENT: 0.3,
    Condition.GOOD: 0.7,
    Condition.FAIR: 1.0,
    Condition.POOR: 1.4,
}

_INTERIOR_RATE = {
    Condition.EXCELLENT: 8,
    Condition.GOOD: 15,
    Condition.FAIR: 25,
    Condition.POOR: 35,
}

# Exterior rate per 坪 before snow-load multiplier
_EXTERIOR_RATE_BY_AGE = [
    (15,  5),
    (25, 12),
    (999, 20),
]


def _age_lookup(table: list[tuple[int, float]], age: int) -> float:
    for limit, rate in table:
        if age < limit:
            return rate
    return table[-1][1]


def _monthly_payment(loan_man: float) -> int:
    r = SAPPORO["mortgage_annual_rate"] / 12
    n = SAPPORO["mortgage_years"] * 12
    loan_yen = loan_man * 10_000
    if r == 0:
        return int(loan_yen / n)
    payment = loan_yen * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)
    return int(round(payment))


def estimate_costs(p: Property) -> RenovationEstimate:
    acquisition = p.price_man * SAPPORO["acquisition_rate"]

    base_reno = 0.0
    interior_reno = 0.0
    exterior_reno = 0.0
    construction = 0.0

    if p.property_type == PropertyType.USED_HOUSE:
        base_rate = _age_lookup(_BASE_RENO_BY_AGE, p.age_years)
        multiplier = _CONDITION_MULTIPLIER[p.condition]
        base_reno = base_rate * multiplier * p.building_tsubo

        interior_reno = _INTERIOR_RATE[p.condition] * p.building_tsubo

        ext_rate = _age_lookup(_EXTERIOR_RATE_BY_AGE, p.age_years)
        exterior_reno = ext_rate * SAPPORO["snow_load_multiplier"] * p.building_tsubo

    elif p.property_type == PropertyType.LAND_NEW:
        construction = SAPPORO["new_build_rate_man_per_tsubo"] * p.building_tsubo

    total_reno = base_reno + interior_reno + exterior_reno
    total_cost = p.price_man + total_reno + construction + acquisition

    loan = total_cost * (1 - SAPPORO["down_payment_rate"])
    monthly = _monthly_payment(loan)

    breakdown = {
        "purchase": p.price_man,
        "base_renovation": base_reno,
        "interior_renovation": interior_reno,
        "exterior_renovation": exterior_reno,
        "construction": construction,
        "acquisition_costs": acquisition,
        "total": total_cost,
    }

    return RenovationEstimate(
        property_id=p.id,
        base_renovation_man=base_reno,
        interior_renovation_man=interior_reno,
        exterior_renovation_man=exterior_reno,
        total_renovation_man=total_reno,
        construction_man=construction,
        acquisition_costs_man=acquisition,
        total_cost_man=total_cost,
        monthly_payment_yen=monthly,
        breakdown=breakdown,
    )
