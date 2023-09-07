import pkgutil
import random
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Self, Optional
from enum import Enum


WEAPON_DATA_JSON = "data/weapondata.json"
JOB_DATA_JSON = "data/jobdata.json"
CHAPTER_UNIT_BLOCKS_JSON = "data/chapter_unit_blocks.json"


@dataclass
class UnitBlock:
    base: int
    count: int

    @classmethod
    def of_object(cls, obj: dict[str, Any]) -> Optional[Self]:
        return UnitBlock(base=int(obj["base"], 16), count=obj["count"])


class WeaponKind(Enum):
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
    RINGS = 0x0C
    DRAGONSTONE = 0x11

    @classmethod
    def of_str(cls, s: str) -> Optional[Self]:
        if s == "Sword":
            return WeaponKind.SWORD
        elif s == "Lance":
            return WeaponKind.LANCE
        elif s == "Axe":
            return WeaponKind.AXE
        elif s == "Bow":
            return WeaponKind.BOW
        elif s == "Staff":
            return WeaponKind.STAFF
        elif s == "Anima":
            return WeaponKind.ANIMA
        elif s == "Light":
            return WeaponKind.LIGHT
        elif s == "Dark":
            return WeaponKind.DARK
        elif s == "Item":
            return WeaponKind.ITEM
        elif s == "Monster Weapon":
            return WeaponKind.MONSTER_WEAPON
        elif s == "Rings":
            return WeaponKind.RINGS
        elif s == "Dragonstone":
            return WeaponKind.DRAGONSTONE
        return None


class WeaponRank(Enum):
    E = 0x1
    D = 0x1F
    C = 0x47
    B = 0x79
    A = 0xB5
    S = 0xFB

    @classmethod
    def of_str(cls, s: str) -> Optional[Self]:
        if s == "E":
            return WeaponRank.E
        elif s == "D":
            return WeaponRank.D
        elif s == "C":
            return WeaponRank.C
        elif s == "B":
            return WeaponRank.B
        elif s == "A":
            return WeaponRank.A
        elif s == "S":
            return WeaponRank.S
        return None


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
            usable_weapons=[WeaponKind.of_str(kind) for kind in obj["usable_weapons"]],
            tags=obj["tags"],
        )


# TODO: ensure that all the progression weapons are usable
class FE8Randomizer:
    unit_blocks: list[UnitBlock]
    weapons_by_id: dict[int, WeaponData]
    weapons_by_rank: dict[WeaponRank, list[WeaponData]]
    jobs_by_id: dict[int, JobData]
    promoted_jobs: list[JobData]
    unpromoted_jobs: list[JobData]
    assigned_player_classes: dict[int, int]
    random: random.Random
    rom: bytearray

    def __init__(self, rom: bytearray, random: random.Random):
        self.random = random
        self.rom = rom
        self.unit_blocks = json.loads(
            pkgutil.get_data(__name__, CHAPTER_UNIT_BLOCKS_JSON).decode("utf-8"),
            object_hook=UnitBlock.of_object,
        )
        item_data = json.loads(
            pkgutil.get_data(__name__, WEAPON_DATA_JSON).decode("utf-8"),
            object_hook=WeaponData.of_object,
        )

        job_data = json.loads(
            pkgutil.get_data(__name__, JOB_DATA_JSON).decode("utf-8"),
            object_hook=JobData.of_object,
        )

        # TODO: handle these properly
        job_data = [job for job in job_data if job.usable_weapons]

        self.assigned_player_classes = dict()

        self.weapons_by_id = {item.id: item for item in item_data}
        self.jobs_by_id = {job.id: job for job in job_data}

        self.promoted_jobs = [job for job in job_data if job.is_promoted]
        self.unpromoted_jobs = [job for job in job_data if not job.is_promoted]

        self.weapons_by_rank = defaultdict(list)

        for weap in self.weapons_by_id.values():
            self.weapons_by_rank[weap.rank].append(weap)

    def select_new_item(self, job: JobData, item_id: int) -> int:
        if item_id not in self.weapons_by_id:
            return item_id

        weapon_attrs: WeaponData = self.weapons_by_id[item_id]

        return random.choice(
            [
                weap
                for weap in self.weapons_by_rank[weapon_attrs.rank]
                if weap.kind in job.usable_weapons
            ]
        ).id

    def randomize_chapter_unit(self, data_offset: int) -> None:
        # We *could* read the full struct, but we only need a few individual
        # bytes, so we may as well extract them ad-hoc.
        unit = self.rom[data_offset : data_offset + 20]
        job_id = unit[1]

        # If the unit's class is is not a "standard" class that can be given to
        # players, it's probably some NPC or enemy that shouldn't be touched.
        if job_id not in self.jobs_by_id:
            return

        job = self.jobs_by_id[job_id]
        char = unit[0]
        is_player = bool(unit[2] & 2)
        inventory = unit[0x10:0x14]

        if char in self.assigned_player_classes:
            # TODO: Orson
            new_job = self.assigned_player_classes[char]
        else:
            new_job_pool = (
                self.promoted_jobs if job.is_promoted else self.unpromoted_jobs
            )
            new_job = self.random.choice(new_job_pool)

            if is_player:
                self.assigned_player_classes[char] = new_job

        new_inventory = [self.select_new_item(job, item) for item in inventory]

        self.rom[data_offset + 1] = new_job.id
        for i, item_id in enumerate(new_inventory):
            self.rom[data_offset + 0x10 + i] = item_id

    def apply_changes(self) -> None:
        for block in self.unit_blocks:
            for i in range(block.count):
                self.randomize_chapter_unit(block.base + i * 20)
