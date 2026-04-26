import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Property, PropertyType, Condition, District, RenovationEstimate, Score
from costs import estimate_costs, SAPPORO
from scorer import score_property
from report import generate_markdown, generate_csv


def _make_property(**kwargs) -> Property:
    defaults = {
        "id": "TEST-001",
        "name": "テスト物件",
        "property_type": PropertyType.USED_HOUSE,
        "district": District.NISHI,
        "price_man": 3000.0,
        "land_tsubo": 150.0,
        "building_tsubo": 50.0,
        "age_years": 20,
        "condition": Condition.FAIR,
        "station_minutes": 10,
        "has_outdoor_space": True,
        "school_district_rating": 3,
        "notes": "",
    }
    defaults.update(kwargs)
    return Property(**defaults)


class TestModels(unittest.TestCase):
    def test_property_from_dict(self):
        d = {
            "id": "X-1",
            "name": "テスト",
            "property_type": "中古一戸建て",
            "district": "西区",
            "price_man": "3000",
            "land_tsubo": "150",
            "building_tsubo": "50",
            "age_years": "10",
            "condition": "good",
            "station_minutes": "12",
            "has_outdoor_space": True,
            "school_district_rating": "4",
        }
        p = Property.from_dict(d)
        self.assertEqual(p.id, "X-1")
        self.assertEqual(p.property_type, PropertyType.USED_HOUSE)
        self.assertEqual(p.district, District.NISHI)
        self.assertEqual(p.price_man, 3000.0)
        self.assertEqual(p.condition, Condition.GOOD)

    def test_invalid_property_type(self):
        with self.assertRaises(ValueError):
            PropertyType("無効な種別")

    def test_district_enum(self):
        self.assertEqual(District("西区"), District.NISHI)
        self.assertEqual(District("北区"), District.KITA)
        self.assertEqual(District("手稲区"), District.TEINE)


class TestCosts(unittest.TestCase):
    def test_used_house_renovation_fair_22yr(self):
        p = _make_property(age_years=22, condition=Condition.FAIR, building_tsubo=50)
        est = estimate_costs(p)
        # base: 10万/坪 × 1.0 × 50 = 500
        # interior: 25 × 50 = 1250
        # exterior: 12 × 1.2 × 50 = 720
        # total reno ≈ 2470
        self.assertGreater(est.total_renovation_man, 2000)
        self.assertLess(est.total_renovation_man, 3000)

    def test_new_house_no_renovation(self):
        p = _make_property(
            property_type=PropertyType.NEW_HOUSE,
            age_years=0,
            condition=Condition.EXCELLENT,
        )
        est = estimate_costs(p)
        self.assertEqual(est.base_renovation_man, 0)
        self.assertEqual(est.interior_renovation_man, 0)
        self.assertEqual(est.exterior_renovation_man, 0)
        self.assertEqual(est.construction_man, 0)

    def test_land_new_construction_cost(self):
        building_tsubo = 60.0
        p = _make_property(
            property_type=PropertyType.LAND_NEW,
            building_tsubo=building_tsubo,
            age_years=0,
            condition=Condition.EXCELLENT,
        )
        est = estimate_costs(p)
        expected = SAPPORO["new_build_rate_man_per_tsubo"] * building_tsubo
        self.assertAlmostEqual(est.construction_man, expected, places=1)
        self.assertEqual(est.total_renovation_man, 0)

    def test_acquisition_cost_percentage(self):
        p = _make_property(price_man=4000)
        est = estimate_costs(p)
        expected = 4000 * SAPPORO["acquisition_rate"]
        self.assertAlmostEqual(est.acquisition_costs_man, expected, places=1)

    def test_mortgage_calculation(self):
        # Loan 4500万円 × 0.9 = 4050万円 at 1.635% for 35 years
        p = _make_property(
            property_type=PropertyType.NEW_HOUSE,
            price_man=4500,
            age_years=0,
            condition=Condition.EXCELLENT,
        )
        est = estimate_costs(p)
        # Rough check: should be in reasonable range for this loan size
        self.assertGreater(est.monthly_payment_yen, 100_000)
        self.assertLess(est.monthly_payment_yen, 200_000)

    def test_poor_condition_higher_than_good(self):
        base = dict(age_years=20, building_tsubo=50)
        p_good = _make_property(condition=Condition.GOOD, **base)
        p_poor = _make_property(condition=Condition.POOR, **base)
        est_good = estimate_costs(p_good)
        est_poor = estimate_costs(p_poor)
        self.assertGreater(est_poor.total_renovation_man, est_good.total_renovation_man)


class TestScorer(unittest.TestCase):
    def test_large_land_max_size_score(self):
        p = _make_property(land_tsubo=300, building_tsubo=100)
        est = estimate_costs(p)
        sc = score_property(p, est)
        self.assertEqual(sc.size_score, 20.0)

    def test_station_8min_high_location(self):
        p = _make_property(station_minutes=8)
        est = estimate_costs(p)
        sc = score_property(p, est)
        # station_pts = (30-8)/30 * 10 ≈ 7.3, district = 10 → total ≈ 17.3
        self.assertGreater(sc.location_score, 15)

    def test_outdoor_space_adds_10(self):
        p_with = _make_property(has_outdoor_space=True)
        p_without = _make_property(has_outdoor_space=False)
        est = estimate_costs(p_with)
        sc_with = score_property(p_with, est)
        sc_without = score_property(p_without, est)
        self.assertAlmostEqual(sc_with.lifestyle_score - sc_without.lifestyle_score, 10.0)

    def test_recommendation_thresholds(self):
        p = _make_property()
        est = estimate_costs(p)

        # Manipulate scores directly by checking boundary conditions
        # Score ≥ 70 → Recommended
        p_rec = _make_property(
            land_tsubo=300, building_tsubo=100,
            station_minutes=1, has_outdoor_space=True,
            school_district_rating=5, age_years=0,
            condition=Condition.EXCELLENT, price_man=1000,
        )
        est_rec = estimate_costs(p_rec)
        sc_rec = score_property(p_rec, est_rec)
        self.assertEqual(sc_rec.recommendation, "Recommended")

        # Score ≤ 50 → Skip
        p_skip = _make_property(
            land_tsubo=50, building_tsubo=10,
            station_minutes=60, has_outdoor_space=False,
            school_district_rating=1, age_years=50,
            condition=Condition.POOR, district=District.OTHER,
            price_man=9000,
        )
        est_skip = estimate_costs(p_skip)
        sc_skip = score_property(p_skip, est_skip)
        self.assertIn(sc_skip.recommendation, ("Skip", "Consider"))

    def test_expensive_low_value_score(self):
        # Very expensive per tsubo → low value score
        p = _make_property(price_man=10000, land_tsubo=100)
        est = estimate_costs(p)
        sc = score_property(p, est)
        self.assertLess(sc.value_score, 5)


class TestReport(unittest.TestCase):
    def _setup(self):
        p = _make_property()
        est = estimate_costs(p)
        sc = score_property(p, est)
        return [p], {p.id: est}, {p.id: sc}

    def test_markdown_report_contains_header(self):
        props, ests, scores = self._setup()
        md = generate_markdown(props, ests, scores)
        self.assertIn("# 物件分析レポート", md)

    def test_csv_output_has_all_ids(self):
        props, ests, scores = self._setup()
        output = generate_csv(props, ests, scores)
        for p in props:
            self.assertIn(p.id, output)

    def test_strategy_comparison_present(self):
        props, ests, scores = self._setup()
        md = generate_markdown(props, ests, scores)
        self.assertIn("戦略別比較", md)


if __name__ == "__main__":
    unittest.main()
