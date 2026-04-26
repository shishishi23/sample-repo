from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class PropertyType(str, Enum):
    USED_HOUSE = "中古一戸建て"
    NEW_HOUSE = "新築一戸建て"
    LAND_NEW = "土地+新築"


class Condition(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class District(str, Enum):
    NISHI = "西区"
    KITA = "北区"
    TEINE = "手稲区"
    OTHER = "その他"


@dataclass
class Property:
    id: str
    name: str
    property_type: PropertyType
    district: District
    price_man: float
    land_tsubo: float
    building_tsubo: float
    age_years: int
    condition: Condition
    station_minutes: int
    has_outdoor_space: bool
    school_district_rating: int  # 1-5
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Property:
        return cls(
            id=d["id"],
            name=d["name"],
            property_type=PropertyType(d["property_type"]),
            district=District(d["district"]),
            price_man=float(d["price_man"]),
            land_tsubo=float(d["land_tsubo"]),
            building_tsubo=float(d["building_tsubo"]),
            age_years=int(d["age_years"]),
            condition=Condition(d["condition"]),
            station_minutes=int(d["station_minutes"]),
            has_outdoor_space=bool(d["has_outdoor_space"]),
            school_district_rating=int(d["school_district_rating"]),
            notes=d.get("notes", ""),
        )


@dataclass
class RenovationEstimate:
    property_id: str
    base_renovation_man: float
    interior_renovation_man: float
    exterior_renovation_man: float
    total_renovation_man: float
    construction_man: float
    acquisition_costs_man: float
    total_cost_man: float
    monthly_payment_yen: int
    breakdown: dict = field(default_factory=dict)


@dataclass
class Score:
    property_id: str
    total: float
    size_score: float
    location_score: float
    condition_score: float
    lifestyle_score: float
    value_score: float
    recommendation: str
