"""Recruit checks and deploy permits: the pool, the goal filter, and the gates."""

from . import FE8TestBase
from ..constants import EARLY_UNITS, MID_UNITS, LATE_UNITS

ALL_UNITS = EARLY_UNITS | MID_UNITS | LATE_UNITS

# Seth sits out of EARLY_PERMITS because his permit is its own option.
EARLY_PERMITS = sorted(f"Deploy {u}" for u in EARLY_UNITS if u != "Seth")
MID_PERMITS = sorted(f"Deploy {u}" for u in MID_UNITS)
LATE_PERMITS = sorted(f"Deploy {u}" for u in LATE_UNITS)


class RecruitTestBase(FE8TestBase):
    # Set by subclasses to the units their goal should be able to recruit.
    # Left empty on classes that aren't testing the goal filter.
    expected_units: frozenset = frozenset()

    def location_names(self) -> set:
        return {loc.name for loc in self.multiworld.get_locations(self.player)}

    def permit_names(self) -> set:
        return {
            item.name
            for item in self.multiworld.itempool
            if item.name.startswith("Deploy ")
        }

    def assert_recruits_match(self) -> None:
        if not self.expected_units:
            return
        names = self.location_names()
        permits = self.permit_names()
        for unit in ALL_UNITS:
            expected = unit in self.expected_units
            self.assertEqual(
                f"{unit} Recruited" in names,
                expected,
                f"{unit} Recruited presence is wrong for this goal",
            )
            # A unit's permit tracks its recruit check: excluded units get
            # neither, and the ROM marks them freely deployable instead.
            if unit != "Seth":
                self.assertEqual(
                    f"Deploy {unit}" in permits,
                    expected,
                    f"Deploy {unit} presence is wrong for this goal",
                )

    def test_location_count_matches(self) -> None:
        self.assertEqual(
            self.world.total_locations(),
            len(self.multiworld.get_locations(self.player)),
        )


# --- The goal filter on recruit checks -------------------------------------


class TestOrsonGoal(RecruitTestBase):
    """Chapter 16 is Myrrh's chapter, so she is in; Syrene joins after it."""

    expected_units = EARLY_UNITS | MID_UNITS
    options = {
        "goal": "DefeatOrson",
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_recruits_match_goal(self) -> None:
        self.assert_recruits_match()

    def test_chapter_16_is_the_goal(self) -> None:
        self.assertIn("Complete Chapter 16", self.location_names())
        self.assertBeatable(False)
        self.collect_all_but([])
        self.assertBeatable(True)

    def test_myrrh_and_chapter_16_are_in_routesplit(self) -> None:
        # Chapter 16 clear is what opens Post-routesplit, so both it and Myrrh
        # (who joins during that chapter) sit on the near side of the boundary.
        for name in ("Complete Chapter 16", "Myrrh Recruited"):
            loc = self.multiworld.get_location(name, self.player)
            self.assertEqual(loc.parent_region.name, "Routesplit", name)


class TestTiradoGoal(RecruitTestBase):
    """Chapter 8 is the last chapter, so only the early tier is reachable."""

    expected_units = EARLY_UNITS
    options = {
        "goal": "DefeatTirado",
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_recruits_match_goal(self) -> None:
        self.assert_recruits_match()

    def test_forde_and_kyle_are_excluded(self) -> None:
        # They join in 5x, but Ephraim's party is "away" until after chapter 8,
        # so their recruit checks never fire on this goal.
        names = self.location_names()
        self.assertNotIn("Forde Recruited", names)
        self.assertNotIn("Kyle Recruited", names)

    def test_beatable_at_chapter_eight(self) -> None:
        # The chapter 8 clear is in the starting region, so this goal is
        # satisfied with no items -- while the rest of the game is still gated.
        self.assertFalse(self.can_reach_region("Routesplit"))
        self.assertBeatable(True)


class TestFormortiisGoal(RecruitTestBase):
    """The default goal reaches everyone; this guards against a regression."""

    expected_units = ALL_UNITS
    options = {
        "goal": "DefeatFormortiis",
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_recruits_match_goal(self) -> None:
        self.assert_recruits_match()


# --- Deploy gates ----------------------------------------------------------


class TestDeployGates(RecruitTestBase):
    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_routesplit_requires_eight_early_permits(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:7])
        self.assertFalse(self.can_reach_region("Routesplit"))
        self.collect_by_name(EARLY_PERMITS[7])
        self.assertTrue(self.can_reach_region("Routesplit"))

    def test_post_routesplit_requires_eleven_permits(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:10])
        self.assertTrue(self.can_reach_region("Routesplit"))
        self.assertFalse(self.can_reach_region("Post-routesplit"))
        self.collect_by_name(EARLY_PERMITS[10])
        self.assertTrue(self.can_reach_region("Post-routesplit"))

    def test_mid_permits_count_toward_second_gate(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:8])
        self.collect_by_name(MID_PERMITS[:3])
        self.assertTrue(self.can_reach_region("Post-routesplit"))

    def test_seth_counts_toward_gate(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:7])
        self.assertFalse(self.can_reach_region("Routesplit"))
        self.collect_by_name("Deploy Seth")
        self.assertTrue(self.can_reach_region("Routesplit"))

    def test_knoll_and_myrrh_require_own_permits(self) -> None:
        self.collect_by_name(EARLY_PERMITS)
        self.collect_by_name("Deploy Seth")
        self.collect_by_name(
            [p for p in MID_PERMITS if p not in ("Deploy Knoll", "Deploy Myrrh")]
        )
        self.assertTrue(self.can_reach_region("Post-routesplit"))

        self.assertFalse(self.can_reach_location("Knoll Recruited"))
        self.collect_by_name("Deploy Knoll")
        self.assertTrue(self.can_reach_location("Knoll Recruited"))

        self.assertFalse(self.can_reach_location("Myrrh Recruited"))
        self.collect_by_name("Deploy Myrrh")
        self.assertTrue(self.can_reach_location("Myrrh Recruited"))

    def test_permits_are_progression(self) -> None:
        permits = [
            item
            for item in self.multiworld.itempool
            if item.name.startswith("Deploy ")
        ]
        # +1 for Seth, who is left out of EARLY_PERMITS.
        self.assertEqual(
            len(permits),
            len(EARLY_PERMITS) + len(MID_PERMITS) + len(LATE_PERMITS) + 1,
        )
        for item in permits:
            self.assertTrue(item.advancement, f"{item.name} should be progression")


class TestProgressiveSethGate(RecruitTestBase):
    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": False,
        "progressive_seth_deployment": True,
    }

    def test_seth_deployable_at_four_progressive_items(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:7])
        seth_items = self.get_items_by_name("Progressive Seth Deployment")
        self.assertEqual(len(seth_items), 4)

        self.collect(seth_items[:3])
        self.assertFalse(self.can_reach_region("Routesplit"))
        self.collect(seth_items[3])
        self.assertTrue(self.can_reach_region("Routesplit"))


class TestBothSmoothOptions(RecruitTestBase):
    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": True,
    }

    def test_routesplit_requires_permits_and_level_caps(self) -> None:
        self.collect_by_name(EARLY_PERMITS[:8])
        self.assertFalse(self.can_reach_region("Routesplit"))
        self.collect(self.get_items_by_name("Progressive Level Cap")[:1])
        self.assertTrue(self.can_reach_region("Routesplit"))


class TestSmoothDeploymentsOff(RecruitTestBase):
    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": False,
        "smooth_level_caps": False,
    }

    def test_permits_are_not_progression(self) -> None:
        permits = [
            item
            for item in self.multiworld.itempool
            if item.name.startswith("Deploy ")
        ]
        for item in permits:
            self.assertFalse(item.advancement, f"{item.name} should not be progression")


class TestWithTowerAndRuins(RecruitTestBase):
    """No assertions of its own; runs the default fill tests on this combo."""

    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": True,
        "tower_enabled": True,
        "ruins_enabled": True,
    }


# --- Recruit checks turned off ---------------------------------------------


class TestRecruitChecksOff(FE8TestBase):
    """No recruit locations and no permits, so the gates must be skipped too."""

    options = {
        "recruit_checks_enabled": False,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_no_permit_items_in_pool(self) -> None:
        for item in self.multiworld.itempool:
            self.assertFalse(
                item.name.startswith("Deploy "),
                f"{item.name} should not be in the pool with recruit checks off",
            )
            self.assertNotEqual(item.name, "Progressive Seth Deployment")

    def test_no_recruit_locations(self) -> None:
        for location in self.multiworld.get_locations(self.player):
            self.assertFalse(
                location.name.endswith(" Recruited"),
                f"{location.name} should not exist with recruit checks off",
            )

    def test_routesplit_reachable_without_permits(self) -> None:
        self.assertTrue(self.can_reach_region("Post-routesplit"))

    def test_location_count_matches(self) -> None:
        self.assertEqual(
            self.world.total_locations(),
            len(self.multiworld.get_locations(self.player)),
        )
