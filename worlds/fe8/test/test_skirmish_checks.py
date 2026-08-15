from . import FE8TestBase

from ..constants import SKIRMISH_EARLY, SKIRMISH_LATE, MELKAEN_SKIRMISH

ALWAYS_AVAILABLE = SKIRMISH_EARLY + SKIRMISH_LATE


class TestSkirmishChecksOff(FE8TestBase):
    options = {
        "skirmishes_enabled": False,
        "ruins_enabled": True,
    }

    def test_no_skirmish_locations(self) -> None:
        for location in self.multiworld.get_locations(self.player):
            self.assertNotIn(
                "Skirmish",
                location.name,
                f"{location.name} should not exist with skirmish checks off",
            )

    def test_location_count_matches(self) -> None:
        self.assertEqual(
            self.world.total_locations(),
            len(self.multiworld.get_locations(self.player)),
        )


class TestSkirmishChecksWithoutRuins(FE8TestBase):
    options = {
        "skirmishes_enabled": True,
        "ruins_enabled": False,
        "goal": "DefeatFormortiis",
    }

    def test_sites_present(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for name in ALWAYS_AVAILABLE:
            self.assertIn(name, names)

    def test_melkaen_absent(self) -> None:
        # Melkaen Coast only spawns skirmishes in the Creature Campaign, which
        # is gated behind the same content as Lagdou Ruins.
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertNotIn(MELKAEN_SKIRMISH, names)

    def test_location_count_matches(self) -> None:
        self.assertEqual(
            self.world.total_locations(),
            len(self.multiworld.get_locations(self.player)),
        )


class TestSkirmishChecksWithRuins(FE8TestBase):
    options = {
        "skirmishes_enabled": True,
        "ruins_enabled": True,
    }

    def test_all_sites_present(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for name in ALWAYS_AVAILABLE + (MELKAEN_SKIRMISH,):
            self.assertIn(name, names)

    def test_location_count_matches(self) -> None:
        self.assertEqual(
            self.world.total_locations(),
            len(self.multiworld.get_locations(self.player)),
        )


class TestSkirmishChecksViaLagdouGoal(FE8TestBase):
    """The Lagdou goal implies ruins checks, which should pull Melkaen in too."""

    options = {
        "skirmishes_enabled": True,
        "ruins_enabled": False,
        "goal": "ClearLagdou",
    }

    def test_melkaen_present(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertIn(MELKAEN_SKIRMISH, names)
