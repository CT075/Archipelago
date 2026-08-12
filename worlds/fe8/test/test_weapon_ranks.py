from contextlib import ExitStack, contextmanager
from random import Random
from unittest import TestCase
from unittest.mock import patch

from ..constants import CHARACTER_COUNT, INVENTORY_INDEX, WRANK_COUNT
from ..fe8py import FE8Randomizer, UnitBlock, WeaponKind, WeaponRank, wrank_offset

# We can't ship a base ROM, so these run against a blank one of the right size
# with only the tables under test filled in.
ROM_SIZE = 0x1000000

# Any nonzero rank works; C is easy to spot in a hex dump.
SENTINEL_RANK = 0x47

BASE_CONFIG = {
    "player_rando": False,
    "player_monster": False,
    "enable_weapon_level_caps": False,
    "easier_5x": False,
    "unbreakable_regalia": False,
    "shuffle_skirmish_tables": False,
    "normalize_genders": False,
    "growth_rando": (0, 10, 70),
    "music_rando": 0,
    "seed": 0,
    "player": 1,
}

# The other steps in `apply_base_changes` read ROM tables we have no data for;
# stubbing them out leaves the weapon-rank path intact.
UNRELATED_STEPS = [
    "fix_movement_costs",
    "fix_cutscenes",
    "tweak_lords",
    "make_monsters_mounted",
]


@contextmanager
def stubbed(steps: list[str]):
    with ExitStack() as stack:
        for step in steps:
            stack.enter_context(
                patch.object(FE8Randomizer, step, lambda *_, **__: None)
            )
        yield


def rank_row(ranks: dict[WeaponKind, int]) -> bytes:
    row = bytearray(WRANK_COUNT)
    for kind, rank in ranks.items():
        row[kind] = rank
    return bytes(row)


def make_randomizer(
    player_rando: bool,
    enable_weapon_level_caps: bool,
    wranks_by_char: dict[int, bytes] = {},
) -> FE8Randomizer:
    rom = bytearray(ROM_SIZE)
    for char in range(CHARACTER_COUNT):
        offset = wrank_offset(char)
        rom[offset : offset + WRANK_COUNT] = bytes([SENTINEL_RANK] * WRANK_COUNT)
    for char, row in wranks_by_char.items():
        offset = wrank_offset(char)
        rom[offset : offset + WRANK_COUNT] = row

    config = {
        **BASE_CONFIG,
        "player_rando": player_rando,
        "enable_weapon_level_caps": enable_weapon_level_caps,
    }
    return FE8Randomizer(rom=rom, random=Random(BASE_CONFIG["seed"]), config=config)


def wranks(randomizer: FE8Randomizer, char: int) -> bytes:
    offset = wrank_offset(char)
    return bytes(randomizer.rom[offset : offset + WRANK_COUNT])


# `randomize_block` only ever reads the unit struct it is pointed at, so we can
# put a block wherever we like in the blank ROM and skip the real chapter data.
FAKE_BLOCK_BASE = 0x900000

SYRENE = 0x21
IRON_SWORD = 1

FALCON_KNIGHT = 73  # sword, lance
WARRIOR = 64  # axe, bow
NECROMANCER = 79  # staff, dark

VANILLA_ROW = rank_row({WeaponKind.SWORD: WeaponRank.A, WeaponKind.LANCE: WeaponRank.C})


def place_unit(randomizer: FE8Randomizer, char: int, job: int, new_job: int) -> None:
    rom = randomizer.rom
    rom[FAKE_BLOCK_BASE] = char
    rom[FAKE_BLOCK_BASE + 1] = job
    rom[FAKE_BLOCK_BASE + 3] = 0  # player affiliation, no autolevel
    rom[FAKE_BLOCK_BASE + INVENTORY_INDEX] = IRON_SWORD
    randomizer.unit_blocks = {
        "test": [UnitBlock(name="test", base=FAKE_BLOCK_BASE, count=1, logic={})]
    }
    # A unit whose class is already in the store reuses it rather than rolling a
    # new one, which is what lets us pin the outcome instead of fishing a seed.
    randomizer.character_store[char] = randomizer.jobs_by_id[new_job]


class TestWeaponRanks(TestCase):
    def test_ranks_cleared_only_when_classes_are_randomized(self) -> None:
        # Shuffled classes are the only reason to drop a unit's personal ranks.
        # Weapon level caps make player units read party-wide ranks instead of
        # the table, so on their own they're not a reason to touch it.
        for player_rando in (False, True):
            for caps in (False, True):
                with self.subTest(player_rando=player_rando, weapon_level_caps=caps):
                    randomizer = make_randomizer(player_rando, caps)
                    with stubbed(UNRELATED_STEPS + ["randomize_block"]):
                        randomizer.apply_base_changes()

                    expected = (
                        bytes(WRANK_COUNT)
                        if player_rando
                        else bytes([SENTINEL_RANK] * WRANK_COUNT)
                    )
                    for name, ids in randomizer.character_store.ids_by_name.items():
                        for char in ids:
                            self.assertEqual(wranks(randomizer, char), expected, name)

    def test_clearing_leaves_unknown_characters_alone(self) -> None:
        # Generic units and unrandomized NPCs aren't ours to rewrite.
        randomizer = make_randomizer(player_rando=True, enable_weapon_level_caps=False)
        randomizer.clear_weapon_ranks()

        untouched = bytes([SENTINEL_RANK] * WRANK_COUNT)
        for char in range(CHARACTER_COUNT):
            known = randomizer.character_store.lookup_name(char) is not None
            expected = bytes(WRANK_COUNT) if known else untouched
            self.assertEqual(wranks(randomizer, char), expected, hex(char))

    def test_vanilla_ranks_survive_clearing(self) -> None:
        # `vanilla_highest_rank` reads the snapshot taken at construction, so
        # clearing the table must not change what it reports.
        for player_rando in (False, True):
            for caps in (False, True):
                with self.subTest(player_rando=player_rando, weapon_level_caps=caps):
                    randomizer = make_randomizer(player_rando, caps)
                    with stubbed(UNRELATED_STEPS + ["randomize_block"]):
                        randomizer.apply_base_changes()

                    for ids in randomizer.character_store.ids_by_name.values():
                        for char in ids:
                            self.assertEqual(
                                randomizer.vanilla_highest_rank(char), SENTINEL_RANK
                            )


class TestReclassedUnitRanks(TestCase):
    def reclass(
        self,
        new_job: int,
        player_rando: bool = True,
        caps: bool = False,
        vanilla_row: bytes = VANILLA_ROW,
    ) -> FE8Randomizer:
        randomizer = make_randomizer(player_rando, caps, {SYRENE: vanilla_row})
        place_unit(randomizer, SYRENE, FALCON_KNIGHT, new_job)
        with stubbed(UNRELATED_STEPS):
            randomizer.apply_base_changes()
        return randomizer

    def test_unit_that_keeps_its_class_keeps_its_ranks(self) -> None:
        # Sword only, with the lance slot empty: a Falcon Knight can use
        # lances, so the reclass path would fill that slot in. Holding onto the
        # vanilla class has to leave the gap alone, which tells the two apart.
        sword_only = rank_row({WeaponKind.SWORD: WeaponRank.A})
        randomizer = self.reclass(FALCON_KNIGHT, vanilla_row=sword_only)

        self.assertEqual(randomizer.rom[FAKE_BLOCK_BASE + 1], FALCON_KNIGHT)
        self.assertEqual(wranks(randomizer, SYRENE), sword_only)

    def test_reclassed_unit_gets_its_ranks_on_its_new_weapon_types(self) -> None:
        randomizer = self.reclass(WARRIOR)
        row = wranks(randomizer, SYRENE)

        self.assertEqual(randomizer.rom[FAKE_BLOCK_BASE + 1], WARRIOR)
        # A Warrior uses axes and bows, and gets exactly the two ranks Syrene
        # came in with — they just move to the weapons she can now hold.
        self.assertEqual(
            sorted([row[WeaponKind.AXE], row[WeaponKind.BOW]]),
            sorted([int(WeaponRank.A), int(WeaponRank.C)]),
        )
        for kind in WeaponKind:
            if kind in (WeaponKind.AXE, WeaponKind.BOW) or kind >= WRANK_COUNT:
                continue
            self.assertEqual(row[kind], 0, kind.name)

    def test_dark_rank_is_floored_to_d(self) -> None:
        # Dark has no E-rank weapon, so an E dark rank would be unusable.
        randomizer = self.reclass(
            NECROMANCER, vanilla_row=rank_row({WeaponKind.SWORD: WeaponRank.E})
        )
        row = wranks(randomizer, SYRENE)

        self.assertEqual(row[WeaponKind.STAFF], int(WeaponRank.E))
        self.assertEqual(row[WeaponKind.DARK], int(WeaponRank.D))

    def test_weapon_level_caps_leave_the_row_cleared(self) -> None:
        # Under caps the table is dead data for player units, so the ranks
        # cleared by `clear_weapon_ranks` are never written back.
        randomizer = self.reclass(WARRIOR, caps=True)

        self.assertEqual(randomizer.rom[FAKE_BLOCK_BASE + 1], WARRIOR)
        self.assertEqual(wranks(randomizer, SYRENE), bytes(WRANK_COUNT))

    def test_unrandomized_player_unit_is_left_alone(self) -> None:
        # Even with another class on offer, a player unit is untouched when
        # class randomization is off — class and ranks both stay vanilla.
        randomizer = self.reclass(WARRIOR, player_rando=False)

        self.assertEqual(randomizer.rom[FAKE_BLOCK_BASE + 1], FALCON_KNIGHT)
        self.assertEqual(wranks(randomizer, SYRENE), VANILLA_ROW)
