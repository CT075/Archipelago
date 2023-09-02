"""
Archipelago World definition for Fire Emblem: Sacred Stones
"""

from typing import ClassVar, Optional, Callable, Set

from ..AutoWorld import World, WebWorld
from BaseClasses import Region, ItemClassification, CollectionState
import settings

from .options import fe8_options
from .constants import (
    FE8_NAME,
    FE8_ID_PREFIX,
    NUM_LEVELCAPS,
    WEAPON_TYPES,
    NUM_WEAPON_LEVELS,
    HOLY_WEAPONS,
)
from .locations import FE8Location
from .items import FE8Item
from .data import locations, items

# from .rom import FE8DeltaPatch


class FE8WebWorld(WebWorld):
    tutorials = []


# CR cam: .
class FE8Settings(settings.Group):
    '''
    class FE8RomFile(settings.UserFilePath):
        """File name of your Fire Emblem: The Sacred Stones (U) ROM"""

        description = "FE8 ROM file"
        copy_to = "Fire Emblem: The Sacred Stones (U).gba"
        md5s = [FE8DeltaPatch.hash]

    rom_file: FE8RomFile(FE8RomFile.copy_to)
    '''

    pass


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
    option_definitions = fe8_options
    settings_key = "fe8_settings"
    settings: ClassVar[FE8Settings]
    topology_present = False
    web = FE8WebWorld()
    progression_holy_weapons: Set[str] = {}

    # TODO: populate for real
    item_name_to_id = {name: id + FE8_ID_PREFIX for name, id in items}
    location_name_to_id = {name: id + FE8_ID_PREFIX for name, id in locations}
    item_name_groups = {"holy weapons": list(HOLY_WEAPONS.keys())}

    def create_item_with_classification(
        self, item: str, cls: ItemClassification
    ) -> FE8Item:
        return FE8Item(
            item,
            cls,
            self.item_name_to_id[item],
            self.player,
        )

    def create_item(self, item: str) -> FE8Item:
        return self.create_item_with_classification(
            self,
            item,
            # specific progression items are set during `create_items`, so we
            # can safely assume that they're filler if created here.
            ItemClassification.filler,
        )

    def create_items(self) -> None:
        min_endgame_level_cap = self.multiworld.min_endgame_level_cap[self.player]
        exclude_latona = self.multiworld.exclude_latona[self.player]
        required_holy_weapons = self.multiworld.required_holy_weapons[self.player]

        needed_level_uncaps = (min_endgame_level_cap - 10) // 5

        for i in range(NUM_LEVELCAPS):
            self.multiworld.itempool.append(
                self.create_item_with_classification(
                    "Progressive Level Cap",
                    ItemClassification.progression
                    if i < needed_level_uncaps
                    else ItemClassification.useful,
                )
            )

        holy_weapon_pool = set(HOLY_WEAPONS.keys())

        if exclude_latona:
            holy_weapon_pool.remove("Latona")

        progression_holy_weapons = self.random.choices(
            list(holy_weapon_pool), k=required_holy_weapons
        )
        progression_weapon_types = {HOLY_WEAPONS[w] for w in progression_holy_weapons}

        self.progression_holy_weapons = progression_holy_weapons

        for wtype in WEAPON_TYPES:
            for _ in range(NUM_WEAPON_LEVELS):
                self.multiworld.itempool.append(
                    self.create_item_with_classification(
                        "Progressive Weapon Level ({})".format(wtype),
                        ItemClassification.progression
                        if wtype in progression_weapon_types
                        else ItemClassification.useful,
                    )
                )

        for hw in HOLY_WEAPONS:
            self.multiworld.itempool.append(
                self.create_item_with_classification(
                    hw,
                    ItemClassification.progression
                    if hw in progression_holy_weapons
                    else ItemClassification.useful,
                )
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
        smooth_level_caps = self.multiworld.smooth_level_caps[self.player]
        min_endgame_level_cap = self.multiworld.min_endgame_level_cap[self.player]

        menu = Region("Menu", self.player, self.multiworld)
        finalboss = Region("FinalBoss", self.player, self.multiworld)

        self.multiworld.regions.append(menu)
        self.multiworld.regions.append(finalboss)

        self.add_location_to_region("Defeat Formortiis", None, finalboss)

        def level_cap_at_least(n: int) -> Callable[CollectionState, bool]:
            def wrapped(state: CollectionState) -> bool:
                return 10 + state.prog_items["Progressive Level Cap"] * 5 >= n

            return wrapped

        def finalboss_rule(state: CollectionState) -> bool:
            if not level_cap_at_least(min_endgame_level_cap)(state):
                return False
            weapons_needed = self.progression_holy_weapons
            weapon_types_needed = {HOLY_WEAPONS[weapon] for weapon in weapons_needed}

            for weapon in weapons_needed:
                if not state[weapon]:
                    return False

            for weapon_type in weapon_types_needed:
                if (
                    state.prog_items[
                        "Progressive Weapon Level ({})".format(weapon_type)
                    ]
                    < NUM_WEAPON_LEVELS
                ):
                    return False

            return True

        if smooth_level_caps:
            prologue = Region("Before Routesplit", self.player, self.multiworld)
            route_split = Region("Routesplit", self.player, self.multiworld)
            lategame = Region("Post-routesplit", self.player, self.multiworld)

            self.multiworld.regions.append(prologue)
            self.multiworld.regions.append(route_split)
            self.multiworld.regions.append(lategame)

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
            self.add_location_to_region("Sieglinde Received", None, lategame)
            self.add_location_to_region("Siegmund Received", None, lategame)
            self.add_location_to_region("Nidhogg Received", None, lategame)
            self.add_location_to_region("Vidofnir Received", None, lategame)
            self.add_location_to_region("Ivaldi Received", None, lategame)
            self.add_location_to_region("Latona Received", None, lategame)

            menu.connect(prologue, "Start Game")
            prologue.add_exits(
                {"Routesplit": "Clear chapter 8"},
                {"Routesplit": level_cap_at_least(15)},
            )
            route_split.add_exits(
                {"Post-routesplit": "Clear chapter 15"},
                {"Post-routesplit": level_cap_at_least(25)},
            )
            lategame.add_exits(
                {"FinalBoss": "Clear chapter 20"},
                {"FinalBoss": finalboss_rule},
            )
        else:
            campaign = Region("MainCampaign", self.player, self.multiworld)

            for name, lid in locations:
                if "Formortiis" not in name:
                    self.add_location_to_region(name, lid, campaign)

            menu.connect(campaign, "Start Game")
            campaign.add_exits(
                {"FinalBoss": "Clear chapter 20"},
                {"FinalBoss": finalboss_rule},
            )

            self.multiworld.regions.append(campaign)
