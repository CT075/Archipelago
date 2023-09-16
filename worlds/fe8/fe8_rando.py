# We deliberately do not import [random] directly to ensure that all random
# functions go through the multiworld rng seed.
from random import Random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Union
from enum import IntEnum
import logging

from .util import fetch_json, write_short_le, read_short_le, read_word_le

DEBUG = False


def debug_print(s: str) -> None:
    if DEBUG:
        print(s)


# CR cam: Maybe these should go into [constants]?

WEAPON_DATA = "data/weapondata.json"
JOB_DATA = "data/jobdata.json"
CHARACTERS = "data/characters.json"
CHAPTER_UNIT_BLOCKS = "data/chapter_unit_blocks.json"

ROM_BASE_ADDRESS = 0x08000000

CHAPTER_UNIT_SIZE = 20
INVENTORY_INDEX = 0xC
INVENTORY_SIZE = 0x4
COORDS_INDEX = 4
REDA_COUNT_INDEX = 7
REDA_PTR_INDEX = 8

CHARACTER_TABLE_BASE = 0x803D30
CHARACTER_SIZE = 52
CHARACTER_WRANK_OFFSET = 20
CHARACTER_STATS_OFFSET = 12

JOB_TABLE_BASE = 0x807110
JOB_SIZE = 84
JOB_STATS_OFFSET = 11

STATS_COUNT = 6  # HP, Str, Skl, Spd, Def, Res (don't need Lck)

EIRIKA = 1
EIRIKA_LORD = 2
EPHRAIM = 15
EPHRAIM_LORD = 1

EIRIKA_RAPIER_OFFSET = 0x9EF088
ROSS_CH2_HP_OFFSET = 0x9F03B8

MOVEMENT_COST_TABLE_BASE = 0x80B808
MOVEMENT_COST_ENTRY_SIZE = 65
MOVEMENT_COST_ENTRY_COUNT = 49
MOVEMENT_COST_SENTINEL = 31

IMPORTANT_TERRAIN_TYPES = [
    14,  # Thicket
    15,  # Sand
    16,  # Desert
    17,  # River
    18,  # Mountain
    19,  # Peak
    20,  # Bridge
    21,  # Bridge 2
    22,  # Sea
    23,  # Lake
    26,  # Fence 1
    39,  # Cliff
    47,  # Building 2
    51,  # Fence 2
    54,  # Sky
    55,  # Deeps
    57,  # Inn
    58,  # Barrel
    59,  # Bone
    60,  # Dark
    61,  # Water
    62,  # Gunnels
]


def encode_unit_coords(x: int, y: int) -> int:
    return y << 6 | x


def int_if_possible(x: str) -> Union[int, str]:
    try:
        return int(x)
    except ValueError:
        return x


class UnitBlock:
    name: str
    base: int
    count: int

    # Currently, the names of blocks in `chapter_unit_blocks.json` are all
    # automatically generated from chapter event disassembly and are tagged
    # with any relevant information about the block. However,
    logic: defaultdict[Union[int, str], dict[str, Any]]

    def __init__(
        self, name: str, base: int, count: int, logic: dict[str, dict[str, Any]]
    ):
        self.name = name
        self.base = base
        self.count = count
        self.logic = defaultdict(
            dict, {int_if_possible(k): v for k, v in logic.items()}
        )


class WeaponKind(IntEnum):
    SWORD = 0x00
    LANCE = 0x01
    AXE = 0x02
    BOW = 0x03
    STAFF = 0x04
    ANIMA = 0x05
    LIGHT = 0x06
    DARK = 0x07
    ITEM = 0x09
    MONSTER_WEAPON = 0x0B
    RING = 0x0C
    DRAGONSTONE = 0x11

    @classmethod
    def of_str(cls, s: str) -> "WeaponKind":
        match s:
            case "Sword":
                return WeaponKind.SWORD
            case "Lance":
                return WeaponKind.LANCE
            case "Axe":
                return WeaponKind.AXE
            case "Bow":
                return WeaponKind.BOW
            case "Staff":
                return WeaponKind.STAFF
            case "Anima":
                return WeaponKind.ANIMA
            case "Light":
                return WeaponKind.LIGHT
            case "Dark":
                return WeaponKind.DARK
            case "Item":
                return WeaponKind.ITEM
            case "Monster Weapon":
                return WeaponKind.MONSTER_WEAPON
            case "Ring":
                return WeaponKind.RING
            case "Dragonstone":
                return WeaponKind.DRAGONSTONE
        raise ValueError

    def damaging(self) -> bool:
        match self:
            case WeaponKind.SWORD:
                return True
            case WeaponKind.LANCE:
                return True
            case WeaponKind.AXE:
                return True
            case WeaponKind.BOW:
                return True
            case WeaponKind.STAFF:
                return False
            case WeaponKind.ANIMA:
                return True
            case WeaponKind.LIGHT:
                return True
            case WeaponKind.DARK:
                return True
            case WeaponKind.ITEM:
                return False
            case WeaponKind.MONSTER_WEAPON:
                return True
            case WeaponKind.RING:
                return False
            case WeaponKind.DRAGONSTONE:
                return True
        raise ValueError


class WeaponRank(IntEnum):
    E = 0x1
    D = 0x1F
    C = 0x47
    B = 0x79
    A = 0xB5
    S = 0xFB

    @classmethod
    def of_str(cls, s: str) -> "WeaponRank":
        match s:
            case "E":
                return WeaponRank.E
            case "D":
                return WeaponRank.D
            case "C":
                return WeaponRank.C
            case "B":
                return WeaponRank.B
            case "A":
                return WeaponRank.A
            case "S":
                return WeaponRank.S
        raise ValueError


@dataclass
class WeaponData:
    id: int
    name: str
    rank: WeaponRank
    kind: WeaponKind
    locks: set[str]

    @classmethod
    def of_object(cls, obj: dict[str, Any]):
        return WeaponData(
            id=obj["id"],
            name=obj["name"],
            rank=WeaponRank.of_str(obj["rank"]),
            kind=WeaponKind.of_str(obj["kind"]),
            locks=obj.get("locks", []),
        )


@dataclass
class JobData:
    id: int
    name: str
    is_promoted: bool
    usable_weapons: set[WeaponKind]
    tags: set[str]

    @classmethod
    def of_object(cls, obj: dict[str, Any]):
        return JobData(
            id=obj["id"],
            name=obj["name"],
            is_promoted=obj["is_promoted"],
            usable_weapons=set(
                WeaponKind.of_str(kind) for kind in obj["usable_weapons"]
            ),
            tags=set(obj["tags"]),
        )


class CharacterStore:
    names_by_id: dict[int, str]
    character_jobs: dict[str, JobData]

    def __init__(self, char_ids: dict[str, list[int]]):
        self.names_by_id = {}

        for name, ids in char_ids.items():
            for i in ids:
                self.names_by_id[i] = name

        self.character_jobs = {}

    def lookup_name(self, char_id: int):
        if char_id not in self.names_by_id:
            return None
        return self.names_by_id[char_id]

    def __setitem__(self, char: Union[int, str], job: JobData):
        if isinstance(char, int):
            if char not in self.names_by_id:
                return
            name = self.names_by_id[char]
        else:
            name = char
        self.character_jobs[name] = job

    def __getitem__(self, char: Union[int, str]):
        name = char if isinstance(char, str) else self.names_by_id[char]
        return self.character_jobs[name]

    def __contains__(self, char: Union[int, str]):
        if isinstance(char, int):
            if char not in self.names_by_id:
                return False
            name = self.names_by_id[char]
        else:
            name = char

        return name in self.character_jobs


def job_valid(job: JobData, logic: dict[str, Any]) -> bool:
    if "must_fly" in logic and logic["must_fly"] and "flying" not in job.tags:
        return False

    if "no_fly" in logic and logic["no_fly"] and "flying" in job.tags:
        return False

    if (
        "must_fight" in logic
        and logic["must_fight"]
        and all(not wtype.damaging() for wtype in job.usable_weapons)
    ):
        return False

    return True


# TODO: Eirika and Ephraim should be able to use their respective weapons if
# they get randomized into the right class.
def weapon_usable(weapon: WeaponData, job: JobData, logic: dict[str, Any]) -> bool:
    if weapon.kind not in job.usable_weapons:
        return False

    if any(lock not in job.tags for lock in weapon.locks):
        return False

    if "must_fight" in logic and weapon.kind in [
        WeaponKind.ITEM,
        WeaponKind.STAFF,
        WeaponKind.RING,
    ]:
        return False

    return True


# TODO: ensure that all the progression weapons are usable
class FE8Randomizer:
    unit_blocks: dict[str, list[UnitBlock]]
    weapons_by_id: dict[int, WeaponData]
    weapons_by_name: dict[str, WeaponData]
    weapons_by_rank: dict[WeaponRank, list[WeaponData]]
    character_store: CharacterStore
    jobs_by_id: dict[int, JobData]
    promoted_jobs: list[JobData]
    unpromoted_jobs: list[JobData]
    random: Random
    rom: bytearray

    def __init__(self, rom: bytearray, random: Random):
        self.random = random
        self.rom = rom
        unit_blocks = fetch_json(CHAPTER_UNIT_BLOCKS)

        self.unit_blocks = {
            name: [UnitBlock(**block) for block in blocks]
            for name, blocks in unit_blocks.items()
        }

        item_data = fetch_json(WEAPON_DATA, object_hook=WeaponData.of_object)

        job_data = fetch_json(
            JOB_DATA,
            object_hook=JobData.of_object,
        )

        # TODO: handle these properly
        job_data = [job for job in job_data if job.usable_weapons]

        self.character_store = CharacterStore(fetch_json(CHARACTERS))

        self.weapons_by_id = {item.id: item for item in item_data}
        self.weapons_by_name = {item.name: item for item in item_data}
        self.jobs_by_id = {job.id: job for job in job_data}

        self.promoted_jobs = [
            job for job in job_data if job.is_promoted and "no_rando" not in job.tags
        ]
        self.unpromoted_jobs = [
            job
            for job in job_data
            if not job.is_promoted and "no_rando" not in job.tags
        ]

        self.weapons_by_rank = defaultdict(list)

        for weap in self.weapons_by_id.values():
            self.weapons_by_rank[weap.rank].append(weap)

        # Dark has no E-ranked weapons, so we add Flux
        self.weapons_by_rank[WeaponRank.E].append(self.weapons_by_name["Flux"])

    def select_new_item(self, job: JobData, item_id: int, logic: dict[str, Any]):
        if item_id not in self.weapons_by_id:
            return item_id

        weapon_attrs: WeaponData = self.weapons_by_id[item_id]

        choices = [
            weap
            for weap in self.weapons_by_rank[weapon_attrs.rank]
            if weapon_usable(weap, job, logic)
        ]

        if not choices:
            import json

            logging.error("LOGIC ERROR: no viable weapons")
            logging.error(f"  job: {job.name}")
            logging.error(f"  logic: {json.dumps(logic, indent=2)}")

        return self.random.choice(choices).id

    def select_new_inventory(
        self, job: JobData, items: bytes, logic: dict[str, Any]
    ) -> list[int]:
        return [
            self.select_new_item(job, item_id, logic) for i, item_id in enumerate(items)
        ]

    def rewrite_coords(self, offset: int, x: int, y: int):
        old_coords = read_short_le(self.rom, offset)
        flags = old_coords & 0b1111000000000000
        new_coords = encode_unit_coords(x, y)
        write_short_le(self.rom, offset, new_coords | flags)

    def randomize_chapter_unit(self, data_offset: int, logic: dict[str, Any]) -> None:
        # We *could* read the full struct, but we only need a few individual
        # bytes, so we may as well extract them ad-hoc.
        unit = self.rom[data_offset : data_offset + CHAPTER_UNIT_SIZE]
        job_id = unit[1]

        # If the unit's class is is not a "standard" class that can be given to
        # players, it's probably some NPC or enemy that shouldn't be touched.
        #
        # CR cam: trainees are broken, do this better
        if job_id not in self.jobs_by_id:
            return

        job = self.jobs_by_id[job_id]
        char = unit[0]

        if DEBUG:
            cname = self.character_store.lookup_name(char)
            if cname is not None:
                debug_print(f"    randomizing {cname}...")
            else:
                debug_print(f"    randomizing unit id {hex(char)}...")

        # Affiliation = bits 1,2; unit is player if they're unset
        is_player = not bool(unit[3] & 0b0110)
        # Autolevel is LSB
        autolevel = unit[3] & 1
        inventory = unit[INVENTORY_INDEX : INVENTORY_INDEX + INVENTORY_SIZE]

        if char in self.character_store:
            new_job = self.character_store[char]
        else:
            new_job_pool = (
                self.promoted_jobs if job.is_promoted else self.unpromoted_jobs
            )
            new_job = self.random.choice(
                [job for job in new_job_pool if job_valid(job, logic)]
            )

            if "no_store" not in logic or not logic["no_store"]:
                self.character_store[char] = new_job

        new_inventory = self.select_new_inventory(new_job, inventory, logic)

        self.rom[data_offset + 1] = new_job.id
        for i, item_id in enumerate(new_inventory):
            self.rom[data_offset + INVENTORY_INDEX + i] = item_id

        # If an NPC isn't autoleveled, it's probably a boss or important NPC of
        # some kind, so we should force its weapon levels in the character
        # table.
        if not is_player and not autolevel and char in self.character_store:
            for item_id in new_inventory:
                if item_id not in self.weapons_by_id:
                    continue
                boss_data_offs = CHARACTER_TABLE_BASE + char * CHARACTER_SIZE
                weapon = self.weapons_by_id[item_id]
                boss_wrank_offs = boss_data_offs + CHARACTER_WRANK_OFFSET + weapon.kind
                rank = self.rom[boss_wrank_offs]
                self.rom[boss_wrank_offs] = max(rank, weapon.rank)

        # TODO: This should probably be split into a different method so it
        # doesn't get `ignore`d.
        if "nudges" in logic:
            nudges = logic["nudges"]

            if "start" in nudges:
                x, y = nudges["start"]
                start_offs = data_offset + COORDS_INDEX
                self.rewrite_coords(start_offs, x, y)

            reda_count = self.rom[data_offset + REDA_COUNT_INDEX]
            redas_addr = read_word_le(self.rom, data_offset + REDA_PTR_INDEX)
            redas_offs = redas_addr - ROM_BASE_ADDRESS

            for i in range(reda_count):
                if str(i) in nudges:
                    x, y = nudges[str(i)]
                    reda_offs = redas_offs + 8 * i
                    self.rewrite_coords(reda_offs, x, y)

    def randomize_block(self, block: UnitBlock):
        debug_print(f"  randomizing block {block.name}:")

        for k, v in list(block.logic.items()):
            if isinstance(k, int):
                continue

            assert isinstance(k, str)

            if isinstance(v, dict) and "at_least" in v:
                affected = self.random.sample(range(block.count), v["at_least"])
            else:
                affected = list(range(block.count))

            for i in affected:
                block.logic[i][k] = True

        for i in range(block.count):
            if "ignore" in block.logic[i] and block.logic[i]["ignore"]:
                continue
            self.randomize_chapter_unit(
                block.base + i * CHAPTER_UNIT_SIZE, block.logic[i]
            )

    def fix_movement_costs(self) -> None:
        """
        Units that spawn over water or mountains can get stuck, causing crashes
        or softlocking if their new class cannot walk on those tiles. To resolve
        this, the basepatch includes a fix allowing units to walk on certain
        terrain types (marked by the sentinel value) if they are otherwise stuck.
        """
        for i in range(MOVEMENT_COST_ENTRY_COUNT):
            entry = MOVEMENT_COST_TABLE_BASE + i * MOVEMENT_COST_ENTRY_SIZE
            for terrain_type in IMPORTANT_TERRAIN_TYPES:
                if self.rom[entry + terrain_type] == 255:
                    self.rom[entry + terrain_type] = MOVEMENT_COST_SENTINEL

    def fix_lord_stats(self) -> None:
        for char, job in [(EIRIKA, EIRIKA_LORD), (EPHRAIM, EPHRAIM_LORD)]:
            # Move some of the lord base stats from the lord classes to the lords
            character_entry = CHARACTER_TABLE_BASE + char * CHARACTER_SIZE
            stats_base = character_entry + CHARACTER_STATS_OFFSET

            lord_entry = JOB_TABLE_BASE + job * JOB_SIZE
            job_stats_base = lord_entry + JOB_STATS_OFFSET

            for i in range(STATS_COUNT):
                roll = self.random.randint(0, 4)
                old_base = self.rom[job_stats_base + i]
                new_personal_base = min(roll, old_base)
                self.rom[stats_base + i] += new_personal_base
                self.rom[stats_base + i] -= new_personal_base

    def apply_cutscene_fixes(self) -> None:
        # Eirika's Rapier is given in a cutscene at the start of the chapter,
        # rather than being in her inventory
        eirika_job = self.character_store["Eirika"]
        if any(wkind != WeaponKind.STAFF for wkind in eirika_job.usable_weapons):
            new_rapier = self.select_new_item(
                eirika_job, self.weapons_by_name["Steel Blade"].id, {}
            )
        else:
            new_rapier = self.random.choice(
                [
                    self.weapons_by_name["Heal"],
                    self.weapons_by_name["Mend"],
                    self.weapons_by_name["Recover"],
                ]
            ).id
        self.rom[EIRIKA_RAPIER_OFFSET] = new_rapier

        # While we force Vanessa to fly to give Ross a fighting chance, it's
        # very possible that she won't be able to lift him. To make it more
        # reasonable to save him, we _also_ set his starting HP.
        self.rom[ROSS_CH2_HP_OFFSET] = 15

    # TODO: logic
    #   - Flying Duessel vs enemy archers in Ephraim 10 may be unbeatable
    #   - Duessel's map is just broken
    def apply_changes(self) -> None:
        for chapter_name, chapter in self.unit_blocks.items():
            debug_print(f"randomizing {chapter_name}:")
            for block in chapter:
                self.randomize_block(block)

        self.fix_movement_costs()
        self.apply_cutscene_fixes()
        self.fix_lord_stats()
        # TODO: Super Formortiis buffs
