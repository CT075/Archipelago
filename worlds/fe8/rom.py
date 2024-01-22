import pkgutil
import bsdiff4  # type: ignore
import os
from random import Random

from BaseClasses import MultiWorld
from worlds.Files import APDeltaPatch
from settings import get_settings

from .items import FE8Item
from .locations import FE8Location
from .constants import FE8_NAME, ROM_BASE_ADDRESS
from .options import FE8Options
from .util import write_short_le
from .connector_config import (
    SLOT_NAME_ADDR,
    SUPER_DEMON_KING_OFFS,
    LOCATION_INFO_OFFS,
    LOCATION_INFO_SIZE,
)
from .fe8py import FE8Randomizer

SLOT_NAME_OFFS = SLOT_NAME_ADDR - ROM_BASE_ADDRESS

BASE_PATCH = "data/base_patch.bsdiff4"
PATCH_FILE_EXT = ".apfe8"

AP_ITEM_KIND = 1
SELF_ITEM_KIND = 2


class FE8DeltaPatch(APDeltaPatch):
    game = FE8_NAME
    hash = "005531fef9efbb642095fb8f64645236"
    patch_file_ending = PATCH_FILE_EXT
    result_file_ending = ".gba"

    @classmethod
    def get_source_data(cls) -> bytes:
        return get_base_rom_as_bytes()


def get_base_rom_as_bytes() -> bytes:
    with open(get_settings().fe8_settings.rom_file, "rb") as infile:
        base_rom_bytes = bytes(infile.read())

    return base_rom_bytes


def rom_location(loc: FE8Location):
    return LOCATION_INFO_OFFS + loc.local_address * LOCATION_INFO_SIZE


def generate_output(
    multiworld: MultiWorld,
    options: FE8Options,
    player: int,
    output_dir: str,
    random: Random,
) -> None:
    base_rom = get_base_rom_as_bytes()
    base_patch = pkgutil.get_data(__name__, BASE_PATCH)
    patched_rom = bytearray(bsdiff4.patch(base_rom, base_patch))

    # CR cam: we could just pass `options`
    config = {
        "player_rando": bool(options.player_unit_rando),
        "player_monster": bool(options.player_unit_monsters),
    }

    randomizer = FE8Randomizer(rom=patched_rom, random=random, config=config)
    randomizer.apply_base_changes()

    if options.shuffle_skirmish_tables:
        randomizer.randomize_monster_gen()

    if options.easier_5x:
        randomizer.apply_5x_buffs()

    if options.unbreakable_regalia:
        randomizer.apply_infinite_holy_weapons()

    for location in multiworld.get_locations(player):
        assert isinstance(location, FE8Location)
        rom_loc = rom_location(location)
        if location.item and location.item.player == player:
            assert isinstance(location.item, FE8Item)
            write_short_le(patched_rom, rom_loc, SELF_ITEM_KIND)
            write_short_le(patched_rom, rom_loc + 2, location.item.local_code)
        else:
            write_short_le(patched_rom, rom_loc, AP_ITEM_KIND)

    patched_rom[SUPER_DEMON_KING_OFFS] = int(bool(options.super_demon_king))

    for i, byte in enumerate(multiworld.player_name[player].encode("utf-8")):
        # TODO: cap length at 63
        patched_rom[SLOT_NAME_OFFS + i] = byte

    outfile_player_name = f"_P{player}"
    outfile_player_name += (
        f"_{multiworld.get_file_safe_player_name(player).replace(' ', '_')}"
        if multiworld.player_name[player] != f"Player{player}"
        else ""
    )

    output_path = os.path.join(
        output_dir, f"AP_{multiworld.seed_name}{outfile_player_name}.gba"
    )
    with open(output_path, "wb") as outfile:
        outfile.write(patched_rom)
    patch = FE8DeltaPatch(
        os.path.splitext(output_path)[0] + PATCH_FILE_EXT,
        player=player,
        player_name=multiworld.player_name[player],
        patched_path=output_path,
    )
    patch.write()
    os.unlink(output_path)
