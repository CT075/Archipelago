# We deliberately do not import [random] directly to ensure that all random
# functions go through the multiworld rng seed.
from random import Random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Union
from enum import IntEnum

from .util import fetch_json, write_short_le, read_short_le, read_word_le

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

CHARACTER_TABLE_OFFSET = 0x803D30
CHARACTER_SIZE = 52
CHARACTER_WRANK_BASE = 20

EIRIKA_RAPIER_OFFSET = 0x9EF088
BONE_COORDS_OFFSET = 0x9F0372

STEEL_BLADE = 0x6
FLUX = 0x45


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

    @classmethod
    def of_object(cls, obj: dict[str, Any]):
        return WeaponData(
            id=obj["id"],
            name=obj["name"],
            rank=WeaponRank.of_str(obj["rank"]),
            kind=WeaponKind.of_str(obj["kind"]),
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
            tags=obj["tags"],
        )


class CharacterStore:
    names_by_id: dict[int, str]
    jobs_by_name: dict[str, JobData]

    def __init__(self, char_ids: dict[str, list[int]]):
        self.names_by_id = {}

        for name, ids in char_ids.items():
            for i in ids:
                self.names_by_id[i] = name

        self.jobs_by_name = {}

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
        self.jobs_by_name[name] = job

    def __getitem__(self, char: Union[int, str]):
        name = char if isinstance(char, str) else self.names_by_id[char]
        return self.jobs_by_name[name]

    def __contains__(self, char: Union[int, str]):
        if isinstance(char, int):
            if char not in self.names_by_id:
                return False
            name = self.names_by_id[char]
        else:
            name = char

        return name in self.jobs_by_name


def job_valid(job: JobData, logic: dict[str, Any]) -> bool:
    if "must_fly" in logic and "flying" not in job.tags:
        return False

    if "no_fly" in logic and "flying" in job.tags:
        return False

    if "must_fight" in logic and all(
        not wtype.damaging() for wtype in job.usable_weapons
    ):
        return False

    return True


def weapon_valid(weapon: WeaponData, logic: dict[str, Any]) -> bool:
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
        self.jobs_by_id = {job.id: job for job in job_data}

        self.promoted_jobs = [job for job in job_data if job.is_promoted]
        self.unpromoted_jobs = [job for job in job_data if not job.is_promoted]

        self.weapons_by_rank = defaultdict(list)

        for weap in self.weapons_by_id.values():
            self.weapons_by_rank[weap.rank].append(weap)

        # Dark has no E-ranked weapons, so we add Flux
        self.weapons_by_rank[WeaponRank.E].append(self.weapons_by_id[FLUX])

    def select_new_item(self, job: JobData, item_id: int, logic: dict[str, Any]):
        if item_id not in self.weapons_by_id:
            return item_id

        weapon_attrs: WeaponData = self.weapons_by_id[item_id]

        choices = [
            weap
            for weap in self.weapons_by_rank[weapon_attrs.rank]
            if weap.kind in job.usable_weapons and weapon_valid(weap, logic)
        ]

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
        if job_id not in self.jobs_by_id:
            return

        job = self.jobs_by_id[job_id]
        char = unit[0]
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

            self.character_store[char] = new_job

        new_inventory = self.select_new_inventory(new_job, inventory, logic)

        self.rom[data_offset + 1] = new_job.id
        for i, item_id in enumerate(new_inventory):
            self.rom[data_offset + INVENTORY_INDEX + i] = item_id

        # If an NPC isn't autoleveled, it's probably a boss or important NPC of
        # some kind, so we should force its weapon levels in the character
        # table.
        if not is_player and not autolevel:
            for item_id in new_inventory:
                if item_id not in self.weapons_by_id:
                    continue
                boss_data_addr = CHARACTER_TABLE_OFFSET + char * CHARACTER_SIZE
                weapon = self.weapons_by_id[item_id]
                boss_wrank_addr = boss_data_addr + CHARACTER_WRANK_BASE + weapon.kind
                rank = self.rom[boss_wrank_addr]
                self.rom[boss_wrank_addr] = max(rank, weapon.rank)

        if "nudge" in logic:
            nudge = logic["nudge"]
            if "start" in nudge:
                x, y = nudge["start"]
                start_offs = data_offset + COORDS_INDEX
                self.rewrite_coords(start_offs, x, y)

            if "end" in nudge:
                reda_count = self.rom[data_offset + REDA_COUNT_INDEX]
                redas_addr = read_word_le(self.rom, data_offset + REDA_PTR_INDEX)
                end_addr = redas_addr + (reda_count - 1) * 8

                end_offs = end_addr - ROM_BASE_ADDRESS
                x, y = nudge["end"]
                self.rewrite_coords(end_offs, x, y)

    def randomize_block(self, block: UnitBlock):
        if "must_fight" in block.logic:
            for i in self.random.sample(
                range(block.count), block.logic["must_fight"]["at_least"]
            ):
                block.logic[i]["must_fight"] = True

        for i in range(block.count):
            self.randomize_chapter_unit(
                block.base + i * CHAPTER_UNIT_SIZE, block.logic[i]
            )

    def apply_cutscene_fixes(self):
        # Eirika's Rapier is given in a cutscene at the start of the chapter,
        # rather than being in her inventory
        eirika_job = self.character_store["Eirika"]
        new_rapier = self.select_new_item(eirika_job, STEEL_BLADE, {})
        self.rom[EIRIKA_RAPIER_OFFSET] = new_rapier

        # The chapter 2 boss moves to an inaccessible mountain tile after his
        # pre-map dialogue.
        self.rom[BONE_COORDS_OFFSET] = 6
        self.rom[BONE_COORDS_OFFSET + 1] = 8

    # TODO: logic
    #   - at least one of L'Arachel or Dozla must be able to fight
    #   - Nudge Cormag to 5,15 (pre) and 6,13 (post) in Eirika 13
    #   - Nudge Cormag to 11,12 in Ephraim 10
    #   - Nudge Tana to 0,5
    #   - Flying Duessel vs enemy archers in that Ephraim map may be unbeatable
    def apply_changes(self) -> None:
        for _chapter_name, chapter in self.unit_blocks.items():
            for block in chapter:
                self.randomize_block(block)

        self.apply_cutscene_fixes()
