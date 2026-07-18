from BaseClasses import ItemClassification

from . import FE8TestBase
from ..connector_config import items

PROMOTION_ITEMS = sorted(name for name, _ in items if name.endswith(" Promotion"))


class TestPromotionUnlocksEnabled(FE8TestBase):
    options = {
        "promotion_unlocks": True,
    }

    def test_expected_item_names(self) -> None:
        self.assertEqual(len(PROMOTION_ITEMS), 23)
        self.assertIn("Paladin Promotion", PROMOTION_ITEMS)
        self.assertIn("Falcon Knight Promotion", PROMOTION_ITEMS)
        # The tier-3 trainee items are named without the "(3)" suffix.
        self.assertIn("Journeyman Promotion", PROMOTION_ITEMS)
        self.assertIn("Recruit Promotion", PROMOTION_ITEMS)
        self.assertIn("Pupil Promotion", PROMOTION_ITEMS)
        # Great Lord is never gated.
        self.assertFalse(any("Great Lord" in name for name in PROMOTION_ITEMS))

    def test_promotion_items_useful_and_unique(self) -> None:
        # With default options there are more useful items than locations, so
        # not every promotion item is guaranteed a slot; but the ones placed
        # must be useful and unique.
        seen = set()
        for item in self.multiworld.itempool:
            if item.name in PROMOTION_ITEMS:
                self.assertEqual(item.classification, ItemClassification.useful)
                self.assertNotIn(item.name, seen)
                seen.add(item.name)
        self.assertGreater(len(seen), 0)


class TestPromotionUnlocksAllFit(FE8TestBase):
    # Tower and Ruins add enough locations for every promotion item to fit.
    options = {
        "promotion_unlocks": True,
        "tower_enabled": True,
        "ruins_enabled": True,
    }

    def test_all_promotion_items_in_pool(self) -> None:
        pool_counts = {name: 0 for name in PROMOTION_ITEMS}
        for item in self.multiworld.itempool:
            if item.name in pool_counts:
                pool_counts[item.name] += 1
        for name, count in pool_counts.items():
            self.assertEqual(count, 1, f"expected exactly one {name} in pool")


class TestPromotionUnlocksDisabled(FE8TestBase):
    options = {
        "promotion_unlocks": False,
    }

    def test_no_promotion_items_in_pool(self) -> None:
        for item in self.multiworld.itempool:
            self.assertNotIn(item.name, PROMOTION_ITEMS)
