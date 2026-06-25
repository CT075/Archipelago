from . import FE8TestBase
from ..constants import DEPLOY_EARLY_UNITS, DEPLOY_MID_UNITS

EARLY_PERMITS = sorted(f"Deploy {u}" for u in DEPLOY_EARLY_UNITS if u != "Seth")
MID_PERMITS = sorted(f"Deploy {u}" for u in DEPLOY_MID_UNITS)


class TestDeployGates(FE8TestBase):
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
        self.collect_by_name([p for p in MID_PERMITS if p != "Deploy Knoll"])
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
        self.assertEqual(len(permits), len(EARLY_PERMITS) + len(MID_PERMITS) + 3)
        for item in permits:
            self.assertTrue(item.advancement, f"{item.name} should be progression")


class TestProgressiveSethGate(FE8TestBase):
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


class TestBothSmoothOptions(FE8TestBase):
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


class TestSmoothDeploymentsOff(FE8TestBase):
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


class TestNoRecruitChecks(FE8TestBase):
    # Smooth deployments without recruit checks: no permits exist, so the
    # gates must be skipped.
    options = {
        "recruit_checks_enabled": False,
        "smooth_deployments": True,
        "smooth_level_caps": False,
    }

    def test_routesplit_reachable_without_permits(self) -> None:
        self.assertTrue(self.can_reach_region("Post-routesplit"))


class TestWithTowerAndRuins(FE8TestBase):
    options = {
        "recruit_checks_enabled": True,
        "smooth_deployments": True,
        "smooth_level_caps": True,
        "tower_enabled": True,
        "ruins_enabled": True,
    }
