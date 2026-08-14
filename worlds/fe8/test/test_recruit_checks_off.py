from . import FE8TestBase


class TestRecruitChecksOffPool(FE8TestBase):
    options = {
        "recruit_checks_enabled": False,
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
