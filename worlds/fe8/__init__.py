"""
Archipelago World definition for Fire Emblem: Sacred Stones
"""

import os
import logging
import hashlib
import pkgutil
from typing import ClassVar, Optional, Callable, Set

from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import (
    components,
    Component,
    Type as ComponentType,
    SuffixIdentifier,
    launch_subprocess,
)
from BaseClasses import Region, ItemClassification, CollectionState
import settings
from Utils import user_path

from .options import fe8_options
from .constants import (
    FE8_NAME,
    FE8_ID_PREFIX,
    NUM_LEVELCAPS,
    WEAPON_TYPES,
    NUM_WEAPON_LEVELS,
    HOLY_WEAPONS,
    CLIENT_TITLE,
)
from .locations import FE8Location
from .items import FE8Item
from .connector_config import locations, items

from .rom import FE8DeltaPatch, generate_output


def launch_client(*args) -> None:
    from .client import launch

    launch_subprocess(launch, name=CLIENT_TITLE)


components.append(
    Component(
        "FE8 Client",
        CLIENT_TITLE,
        component_type=ComponentType.CLIENT,
        func=launch_client,
        file_identifier=SuffixIdentifier(".apfe8"),
    )
)

try:
    connector_script_path = os.path.join(user_path("data", "lua"), "connector_fe8.lua")

    if not os.path.exists(connector_script_path):
        with open(connector_script_path, "wb") as connector_script_file:
            connector = pkgutil.get_data(__name__, "data/connector_fe8.lua")
            if connector is None:
                raise IOError
            connector_script_file.write(connector)
    else:
        with open(connector_script_path, "rb+") as connector_script_file:
            expected_script = pkgutil.get_data(__name__, "data/connector_fe8.lua")
            if expected_script is None:
                raise IOError
            expected_hash = hashlib.md5(expected_script).digest()
            existing_hash = hashlib.md5(connector_script_file.read()).digest()

            if existing_hash != expected_hash:
                connector_script_file.seek(0)
                connector_script_file.truncate()
                connector_script_file.write(expected_script)
except IOError:
    logging.warning(
        "Unable to copy connector_fe8.lua to /data/lua in your Archipelago install."
    )


class FE8WebWorld(WebWorld):
    tutorials = []


class FE8Settings(settings.Group):
    class FE8RomFile(settings.UserFilePath):
        """File name of your Fire Emblem: The Sacred Stones (U) ROM"""

        description = "FE8 ROM file"
        copy_to = "Fire Emblem: The Sacred Stones (U).gba"
        md5s = [FE8DeltaPatch.hash]

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
    option_definitions = fe8_options
    settings_key = "fe8_settings"
    settings: ClassVar[FE8Settings]
    topology_present = False
    web = FE8WebWorld()
    progression_holy_weapons: Set[str] = set()

    # TODO: populate for real
    item_name_to_id = {name: id + FE8_ID_PREFIX for name, id in items}
    location_name_to_id = {name: id + FE8_ID_PREFIX for name, id in locations}
    item_name_groups = {"holy weapons": set(HOLY_WEAPONS.keys())}

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
        smooth_level_caps = self.multiworld.smooth_level_caps[self.player]
        min_endgame_level_cap = self.multiworld.min_endgame_level_cap[self.player]
        exclude_latona = self.multiworld.exclude_latona[self.player]
        required_holy_weapons = self.multiworld.required_holy_weapons[self.player]

        smooth_levelcap_max = 25 if smooth_level_caps else 10

        needed_level_uncaps = (
            max(min_endgame_level_cap, smooth_levelcap_max) - 10
        ) // 5

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

        progression_holy_weapons = self.random.sample(
            list(holy_weapon_pool), k=int(required_holy_weapons)
        )
        progression_weapon_types = {HOLY_WEAPONS[w] for w in progression_holy_weapons}

        self.progression_holy_weapons = set(progression_holy_weapons)

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

        def level_cap_at_least(n: int) -> Callable[[CollectionState], bool]:
            def wrapped(state: CollectionState) -> bool:
                return 10 + state.count("Progressive Level Cap", self.player) * 5 >= n

            return wrapped

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
            self.add_location_to_region("Defeat Lyon", None, lategame)
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

    def generate_output(self, output_directory: str) -> None:
        generate_output(self.multiworld, self.player, output_directory, self.random)
