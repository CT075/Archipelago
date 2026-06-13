"""
Archipelago World definition for Fire Emblem: Sacred Stones
"""

from typing import ClassVar, Optional, Callable, Set, Tuple, Any
import os
import pkgutil

# import logging

from Options import OptionError
from worlds.AutoWorld import World, WebWorld
from BaseClasses import (
    Region,
    ItemClassification,
    CollectionState,
    Tutorial,
)
import settings

from .client import FE8Client
from .options import FE8Options
from .constants import (
    FE8_NAME,
    FE8_ID_PREFIX,
    NUM_LEVELCAPS,
    WEAPON_TYPES,
    NUM_WEAPON_LEVELS,
    HOLY_WEAPONS,
    FILLER_ITEMS,
    DEPLOY_EARLY_UNITS,
    DEPLOY_MID_UNITS,
)
from .locations import FE8Location
from .items import FE8Item
from .connector_config import locations, items

from .rom import FE8ProcedurePatch, write_tokens

# We need to import FE8Client to register it properly, so we use it to disable
# the unused import warning
_ = FE8Client



class FE8WebWorld(WebWorld):
    """
    Webhost info for FE8
    """

    theme = "stone"
    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing FE8 with Archipelago",
        "English",
        "setup_en.md",
        "setup/en",
        ["CT075"],
    )

    tutorials = []


class FE8Settings(settings.Group):
    class FE8RomFile(settings.UserFilePath):
        """File name of your Fire Emblem: The Sacred Stones (U) ROM"""

        description = "FE8 ROM file"
        copy_to = "Fire Emblem The Sacred Stones (U).gba"
        md5s = [FE8ProcedurePatch.hash]

    rom_file: FE8RomFile = FE8RomFile(FE8RomFile.copy_to)


class FE8World(World):
    """
    Fire Emblem: The Sacred Stones is a tactical role-playing game developed by
    Intelligent Systems, and published by Nintendo for the Game Boy Advance
    handheld video game console in 2004 for Japan and 2005 in the West. It is
    the eighth entry in the Fire Emblem series, the second to be released
    outside Japan, and the third and final title to be developed for the Game
    Boy Advance after The Binding Blade and its prequel Fire Emblem.

    Build an army. Trust no one.
    """

    game = FE8_NAME
    base_id = FE8_ID_PREFIX
    options_dataclass = FE8Options
    settings_key = "fe8_settings"
    settings: ClassVar[FE8Settings]
    topology_present = False
    web = FE8WebWorld()
    progression_holy_weapons: Set[str] = set()
    options: FE8Options

    # TODO: populate for real
    item_name_to_id = {name: id + FE8_ID_PREFIX for name, id in items}
    location_name_to_id = {name: id + FE8_ID_PREFIX for name, id in locations}
    item_name_groups = {"holy weapons": set(HOLY_WEAPONS.keys())}

    def total_locations(self) -> int:
        tower_checks_enabled = self.options.tower_checks_enabled()
        ruins_checks_enabled = self.options.ruins_checks_enabled()
        recruit_checks_enabled = bool(self.options.recruit_checks_enabled)

        def is_included(loc: Tuple[str, int]):
            name = loc[0]
            if "Valni" in name and not tower_checks_enabled:
                return False
            if "Lagdou" in name and not ruins_checks_enabled:
                return False
            if "Recruited" in name and not recruit_checks_enabled:
                return False
            return True

        return len([loc for loc in locations if is_included(loc)])

    def create_item_with_classification(
        self, item: str, cls: ItemClassification
    ) -> FE8Item:
        return FE8Item(
            item,
            cls,
            # CR cam: the `FE8Item` constructor also adds `FE8_ID_PREFIX`, so
            # we need to subtract it here, which is awful.
            self.item_name_to_id[item] - FE8_ID_PREFIX,
            self.player,
        )

    def create_item(self, item: str) -> FE8Item:
        return self.create_item_with_classification(
            item,
            # specific progression items are set during `create_items`, so we
            # can safely assume that they're filler if created here.
            ItemClassification.filler,
        )

    def create_items(self) -> None:
        smooth_level_caps = self.options.smooth_level_caps
        min_endgame_level_cap = int(self.options.min_endgame_level_cap)
        exclude_latona = self.options.exclude_latona
        required_holy_weapons = self.options.required_holy_weapons

        smooth_levelcap_max = 25 if smooth_level_caps else 10

        needed_level_uncaps = (
            max(min_endgame_level_cap, smooth_levelcap_max) - 10
        ) // 5

        progression_items: list[FE8Item] = []
        other_items: list[FE8Item] = []

        def register(name: str, cls: ItemClassification):
            (
                progression_items
                if cls == ItemClassification.progression
                else other_items
            ).append(self.create_item_with_classification(name, cls))

        for i in range(NUM_LEVELCAPS):
            register(
                "Progressive Level Cap",
                (
                    ItemClassification.progression
                    if i < needed_level_uncaps
                    else ItemClassification.useful
                ),
            )

        holy_weapon_pool = set(HOLY_WEAPONS.keys())

        if exclude_latona:
            holy_weapon_pool.remove("Latona")

        if int(required_holy_weapons) > len(holy_weapon_pool):
            raise OptionError(
                "too many required holy weapons ({int(required_holy_weapons)})"
            )

        progression_holy_weapons = self.random.sample(
            list(holy_weapon_pool), k=int(required_holy_weapons)
        )
        progression_weapon_types = set(
            HOLY_WEAPONS[w] for w in progression_holy_weapons
        )

        self.progression_holy_weapons = set(progression_holy_weapons)

        for wtype in WEAPON_TYPES:
            for _ in range(NUM_WEAPON_LEVELS):
                register(
                    "Progressive Weapon Level ({})".format(wtype),
                    (
                        ItemClassification.progression
                        if wtype in progression_weapon_types
                        else ItemClassification.useful
                    ),
                )

        if self.options.recruit_checks_enabled:
            progressive_seth = bool(self.options.progressive_seth_deployment)
            # With smooth deployments, region exits and the Knoll/Myrrh recruit
            # checks have rules counting deploy permits, so the permits must be
            # progression for fill logic to see them.
            deploy_classification = (
                ItemClassification.progression
                if self.options.smooth_deployments
                else ItemClassification.useful
            )
            for name, _ in items:
                if name == "Deploy Seth":
                    if not progressive_seth:
                        register(name, deploy_classification)
                elif name == "Progressive Seth Deployment":
                    if progressive_seth:
                        for _ in range(4):
                            register(name, deploy_classification)
                elif "Deploy" in name:
                    register(name, deploy_classification)

        # We shuffle here to ensure that level caps and weapon levels come before
        # holy weapons in `other_weapons`.
        self.random.shuffle(other_items)

        holy_weapons = [name for name in HOLY_WEAPONS.keys()]
        self.random.shuffle(holy_weapons)

        for hw in holy_weapons:
            register(
                hw,
                (
                    ItemClassification.progression
                    if hw in progression_holy_weapons
                    else ItemClassification.useful
                ),
            )

        total_locations = self.total_locations()

        if len(progression_items) > total_locations:
            raise OptionError(
                "Could not place all requested weapon levels, level uncaps, "
                "and deploy permits. Reduce the number of required Holy "
                "Weapons or disable smooth level caps or smooth deployments."
            )

        for item in progression_items:
            self.multiworld.itempool.append(item)

        for _ in range(len(progression_items), total_locations):
            if other_items:
                self.multiworld.itempool.append(other_items.pop())
            else:
                self.multiworld.itempool.append(
                    self.create_item(self.random.choice(FILLER_ITEMS))
                )

    def add_location_to_region(self, name: str, addr: Optional[int], region: Region):
        if addr is None:
            # CR cam: we do the subtract here because `FE8Location` adds it
            # back, which is just awful.
            address = self.location_name_to_id[name] - FE8_ID_PREFIX
        else:
            address = addr
        region.locations.append(FE8Location(self.player, name, address, region))

    def create_regions(self) -> None:
        min_endgame_level_cap = int(self.options.min_endgame_level_cap)
        smooth_level_caps = self.options.smooth_level_caps
        smooth_deployments = self.options.smooth_deployments
        use_three_regions = bool(smooth_level_caps) or bool(smooth_deployments)

        menu = Region("Menu", self.player, self.multiworld)
        finalboss = Region("FinalBoss", self.player, self.multiworld)
        self.multiworld.regions += [menu, finalboss]

        self.add_location_to_region("Defeat Formortiis", None, finalboss)

        def level_cap_at_least(n: int) -> Callable[[CollectionState], bool]:
            player = self.player

            def wrapped(state: CollectionState) -> bool:
                return 10 + state.count("Progressive Level Cap", player) * 5 >= n

            return wrapped

        def deployable_at_least(
            n: int, units: frozenset[str]
        ) -> Callable[[CollectionState], bool]:
            player = self.player
            progressive_seth = bool(self.options.progressive_seth_deployment)
            permits = [f"Deploy {unit}" for unit in units if unit != "Seth"]

            def wrapped(state: CollectionState) -> bool:
                count = sum(1 for permit in permits if state.has(permit, player))
                if "Seth" in units:
                    if progressive_seth:
                        count += (
                            state.count("Progressive Seth Deployment", player) >= 4
                        )
                    else:
                        count += state.has("Deploy Seth", player)
                return count >= n

            return wrapped

        def combine_rules(
            rules: list[Callable[[CollectionState], bool]]
        ) -> Optional[Callable[[CollectionState], bool]]:
            if not rules:
                return None
            if len(rules) == 1:
                return rules[0]
            return lambda state: all(rule(state) for rule in rules)

        def finalboss_rule(state: CollectionState) -> bool:
            if not level_cap_at_least(min_endgame_level_cap)(state):
                return False
            weapons_needed = self.progression_holy_weapons
            weapon_types_needed = {HOLY_WEAPONS[weapon] for weapon in weapons_needed}

            for weapon in weapons_needed:
                if not state.has(weapon, self.player):
                    return False

            for weapon_type in weapon_types_needed:
                if (
                    state.count(
                        "Progressive Weapon Level ({})".format(weapon_type), self.player
                    )
                    < NUM_WEAPON_LEVELS
                ):
                    return False

            return True

        if use_three_regions:
            prologue = Region("Before Routesplit", self.player, self.multiworld)
            route_split = Region("Routesplit", self.player, self.multiworld)
            lategame = Region("Post-routesplit", self.player, self.multiworld)

            self.multiworld.regions += [prologue, route_split, lategame]

            self.add_location_to_region("Complete Prologue", None, prologue)
            self.add_location_to_region("Complete Chapter 1", None, prologue)
            self.add_location_to_region("Complete Chapter 2", None, prologue)
            self.add_location_to_region("Complete Chapter 3", None, prologue)
            self.add_location_to_region("Complete Chapter 4", None, prologue)
            self.add_location_to_region("Complete Chapter 5", None, prologue)
            self.add_location_to_region("Complete Chapter 5x", None, prologue)
            self.add_location_to_region("Complete Chapter 6", None, prologue)
            self.add_location_to_region("Complete Chapter 7", None, prologue)
            self.add_location_to_region("Complete Chapter 8", None, prologue)

            self.add_location_to_region("Complete Chapter 9", None, route_split)
            self.add_location_to_region("Complete Chapter 10", None, route_split)
            self.add_location_to_region("Complete Chapter 11", None, route_split)
            self.add_location_to_region("Complete Chapter 12", None, route_split)
            self.add_location_to_region("Complete Chapter 13", None, route_split)
            self.add_location_to_region("Complete Chapter 14", None, route_split)
            self.add_location_to_region("Complete Chapter 15", None, route_split)
            self.add_location_to_region("Garm Received", None, route_split)
            self.add_location_to_region("Gleipnir Received", None, route_split)
            self.add_location_to_region("Audhulma Received", None, route_split)
            self.add_location_to_region("Excalibur Received", None, route_split)

            self.add_location_to_region("Complete Chapter 16", None, lategame)
            self.add_location_to_region("Complete Chapter 17", None, lategame)
            self.add_location_to_region("Complete Chapter 18", None, lategame)
            self.add_location_to_region("Complete Chapter 19", None, lategame)
            self.add_location_to_region("Complete Chapter 20", None, lategame)
            self.add_location_to_region("Defeat Lyon", None, lategame)
            self.add_location_to_region("Sieglinde Received", None, lategame)
            self.add_location_to_region("Siegmund Received", None, lategame)
            self.add_location_to_region("Nidhogg Received", None, lategame)
            self.add_location_to_region("Vidofnir Received", None, lategame)
            self.add_location_to_region("Ivaldi Received", None, lategame)
            self.add_location_to_region("Latona Received", None, lategame)

            if self.options.recruit_checks_enabled:
                if smooth_deployments:
                    for name, _ in locations:
                        if "Recruited" not in name:
                            continue
                        unit = name.replace(" Recruited", "")
                        if unit in DEPLOY_EARLY_UNITS:
                            self.add_location_to_region(name, None, prologue)
                        elif unit in DEPLOY_MID_UNITS:
                            self.add_location_to_region(name, None, route_split)
                        else:
                            self.add_location_to_region(name, None, lategame)
                else:
                    for name, _ in locations:
                        if "Recruited" in name:
                            self.add_location_to_region(name, None, prologue)

            menu.connect(prologue, "Start Game")

            deploy_gates = bool(smooth_deployments) and bool(
                self.options.recruit_checks_enabled
            )

            routesplit_rules = []
            post_routesplit_rules = []
            if smooth_level_caps:
                routesplit_rules.append(level_cap_at_least(15))
                post_routesplit_rules.append(level_cap_at_least(25))
            if deploy_gates:
                # Chapter 8 has 9 deploy slots (1 forced), chapter 15 has 12
                # (1 forced); logic expects a full roster for each.
                routesplit_rules.append(deployable_at_least(8, DEPLOY_EARLY_UNITS))
                post_routesplit_rules.append(
                    deployable_at_least(11, DEPLOY_EARLY_UNITS | DEPLOY_MID_UNITS)
                )

            routesplit_rule = combine_rules(routesplit_rules)
            post_routesplit_rule = combine_rules(post_routesplit_rules)

            prologue.add_exits(
                {"Routesplit": "Clear chapter 8"},
                {"Routesplit": routesplit_rule} if routesplit_rule else None,
            )
            route_split.add_exits(
                {"Post-routesplit": "Clear chapter 15"},
                (
                    {"Post-routesplit": post_routesplit_rule}
                    if post_routesplit_rule
                    else None
                ),
            )

            lategame.add_exits(
                {"FinalBoss": "Clear chapter 20"},
                {"FinalBoss": finalboss_rule},
            )

            if self.options.tower_checks_enabled():
                tower = Region("Tower of Valni", self.player, self.multiworld)
                self.multiworld.regions.append(tower)

                self.add_location_to_region("Complete Tower of Valni 1", None, tower)
                self.add_location_to_region("Complete Tower of Valni 2", None, tower)
                self.add_location_to_region("Complete Tower of Valni 3", None, tower)
                self.add_location_to_region("Complete Tower of Valni 4", None, tower)
                self.add_location_to_region("Complete Tower of Valni 5", None, tower)
                self.add_location_to_region("Complete Tower of Valni 6", None, tower)
                self.add_location_to_region("Complete Tower of Valni 7", None, tower)
                self.add_location_to_region("Complete Tower of Valni 8", None, tower)

                if smooth_level_caps:
                    route_split.add_exits(
                        {"Tower of Valni": "Complete Chapter 15"},
                        {"Tower of Valni": level_cap_at_least(20)},
                    )
                    tower.add_exits(
                        {"Post-routesplit": "Complete Tower of Valni 8"},
                        {"Post-routesplit": level_cap_at_least(25)},
                    )
                else:
                    route_split.add_exits({"Tower of Valni": "Complete Chapter 15"})
                    tower.add_exits({"Post-routesplit": "Complete Tower of Valni 8"})

            if self.options.ruins_checks_enabled():
                ruins = Region("Lagdou Ruins", self.player, self.multiworld)
                self.multiworld.regions.append(ruins)

                self.add_location_to_region("Complete Lagdou Ruins 1", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 2", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 3", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 4", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 5", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 6", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 7", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 8", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 9", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 10", None, ruins)

                if smooth_level_caps:
                    lategame.add_exits(
                        {"Lagdou Ruins": "Complete Chapter 19"},
                        {"Lagdou Ruins": finalboss_rule},
                    )
                else:
                    lategame.add_exits({"Lagdou Ruins": "Complete Chapter 19"})
                ruins.add_exits({"Post-routesplit": "Complete Lagdou Ruins 10"})

        else:
            campaign = Region("Campaign", self.player, self.multiworld)

            recruit_checks_enabled = bool(self.options.recruit_checks_enabled)
            for name, lid in locations:
                # TODO (cam): do this better
                if any(item in name for item in ("Formortiis", "Valni", "Lagdou")):
                    continue
                if "Recruited" in name and not recruit_checks_enabled:
                    continue
                self.add_location_to_region(name, lid, campaign)

            menu.connect(campaign, "Start Game")
            campaign.add_exits(
                {"FinalBoss": "Clear chapter 20"},
                {"FinalBoss": finalboss_rule},
            )

            self.multiworld.regions.append(campaign)

            if self.options.tower_checks_enabled():
                tower = Region("Tower of Valni", self.player, self.multiworld)
                self.multiworld.regions.append(tower)

                self.add_location_to_region("Complete Tower of Valni 1", None, tower)
                self.add_location_to_region("Complete Tower of Valni 2", None, tower)
                self.add_location_to_region("Complete Tower of Valni 3", None, tower)
                self.add_location_to_region("Complete Tower of Valni 4", None, tower)
                self.add_location_to_region("Complete Tower of Valni 5", None, tower)
                self.add_location_to_region("Complete Tower of Valni 6", None, tower)
                self.add_location_to_region("Complete Tower of Valni 7", None, tower)
                self.add_location_to_region("Complete Tower of Valni 8", None, tower)

                campaign.add_exits({"Tower of Valni": "Complete Chapter 15"})
                tower.add_exits({"Campaign": "Complete Tower of Valni 8"})

            if self.options.ruins_checks_enabled():
                ruins = Region("Lagdou Ruins", self.player, self.multiworld)
                self.multiworld.regions.append(ruins)

                self.add_location_to_region("Complete Lagdou Ruins 1", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 2", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 3", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 4", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 5", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 6", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 7", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 8", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 9", None, ruins)
                self.add_location_to_region("Complete Lagdou Ruins 10", None, ruins)

                campaign.add_exits({"Lagdou Ruins": "Complete Chapter 19"})
                ruins.add_exits({"Campaign": "Complete Lagdou Ruins 10"})

    def set_rules(self) -> None:
        if not self.options.recruit_checks_enabled:
            return
        smooth_deployments = bool(self.options.smooth_deployments)
        for unit in ("Knoll", "Myrrh"):
            loc = self.multiworld.get_location(f"{unit} Recruited", self.player)
            deploy_name = f"Deploy {unit}"
            loc.item_rule = lambda item, n=deploy_name: not (
                item.player == self.player and item.name == n
            )
            if smooth_deployments:
                # These units must be deployed to be recruited. Without smooth
                # deployments the permits aren't progression, so fill logic
                # couldn't satisfy this rule; the item_rule above is the best
                # we can do there.
                loc.access_rule = lambda state, n=deploy_name: state.has(
                    n, self.player
                )

    def fill_slot_data(self) -> dict[str, Any]:
        slot_data = self.options.as_dict("goal")
        return slot_data

    def generate_output(self, output_directory: str) -> None:
        patch = FE8ProcedurePatch(
            player=self.player, player_name=self.multiworld.player_name[self.player]
        )
        basepatch = pkgutil.get_data(__name__, "data/base_patch.bsdiff4")
        assert basepatch is not None
        patch.write_file("base_patch.bsdiff4", basepatch)
        write_tokens(self, patch)
        rom_path = os.path.join(
            output_directory,
            f"{self.multiworld.get_out_file_name_base(self.player)}"
            f"{patch.patch_file_ending}",
        )
        patch.write(rom_path)
