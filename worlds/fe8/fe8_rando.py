import pkgutil

# We deliberately do not import [random] directly to ensure that all random
# functions go through the multiworld rng seed.
from random import Random
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Self, Optional, NamedTuple, Union
from enum import IntEnum

# CR cam: Maybe these should go into [constants]?

WEAPON_DATA_JSON = "data/weapondata.json"
JOB_DATA_JSON = "data/jobdata.json"
CHARACTERS_JSON = "data/characters.json"
CHAPTER_UNIT_BLOCKS_JSON = "data/chapter_unit_blocks.json"

CHAPTER_UNIT_SIZE = 20
INVENTORY_INDEX = 0xC
INVENTORY_SIZE = 0x4
CHARACTER_TABLE_OFFSET = 0x803D30

EIRIKA_RAPIER_OFFSET = 0x9EF088

STEEL_BLADE = 0x6
FLUX = 0x45


@dataclass
class UnitBlock:
    name: str
    base: int
    count: int
    tags: list[str]


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


class WeaponRank(IntEnum):
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


# TODO: ensure that all the progression weapons are usable
class FE8Randomizer:
    unit_blocks: dict[str, UnitBlock]
    weapons_by_id: dict[int, WeaponData]
    weapons_by_rank: dict[WeaponRank, list[WeaponData]]
    recurring_characters: CharacterStore
    jobs_by_id: dict[int, JobData]
    promoted_jobs: list[JobData]
    unpromoted_jobs: list[JobData]
    random: Random
    rom: bytearray

    def __init__(self, rom: bytearray, random: Random):
        self.random = random
        self.rom = rom
        unit_blocks = json.loads(
            pkgutil.get_data(__name__, CHAPTER_UNIT_BLOCKS_JSON).decode("utf-8"),
        )
        self.unit_blocks = {
            name: [UnitBlock(**block) for block in blocks]
            for name, blocks in unit_blocks.items()
        }

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

        self.recurring_characters = CharacterStore(
            json.loads(
                pkgutil.get_data(__name__, CHARACTERS_JSON).decode("utf-8"),
            )
        )

        self.weapons_by_id = {item.id: item for item in item_data}
        self.jobs_by_id = {job.id: job for job in job_data}

        self.promoted_jobs = [job for job in job_data if job.is_promoted]
        self.unpromoted_jobs = [job for job in job_data if not job.is_promoted]

        self.weapons_by_rank = defaultdict(list)

        for weap in self.weapons_by_id.values():
            self.weapons_by_rank[weap.rank].append(weap)

        # Dark has no E-ranked weapons, so we add Flux
        self.weapons_by_rank[WeaponRank.E].append(self.weapons_by_id[FLUX])

    def unit_must_fight(self, offset: int, char_id: int, chapter_name: str) -> bool:
        char = self.recurring_characters.lookup_name(char_id)

        if char is None:
            return False

        # Prologue Valter must be able to fight Seth, and Seth must be able to
        # fight back
        if chapter_name == "Prologue":
            if char in ["Seth", "Valter"]:
                return True

        # At least one of Ephraim, Forde, Kyle and Orson should be able to
        # fight. Orson is the natural choice, as he cannot be randomized into
        # a staff-only class anyway.
        #
        # CR cam: In theory, if Ephraim/Forde/Kyle are all combatants, Orson
        # may not have enough weapon uses to get through 5x..
        if chapter_name == "Ch5x":
            if char == "Orson":
                return True

        # Glen must be able to fight Valter
        if char == "Glen":
            return True

        # Dozla and L'arachel appear as NPCs a few times; he should be able to
        # fight in both of them.
        if char == "Dozla":
            return True

        return False

    def select_new_inventory(
        self, job: JobData, items: bytes, at_least_one_weapon: bool
    ) -> list[int]:
        return [
            # If `at_least_one_weapon`, we force the first item in inventory to
            # be a weapon. In theory, this could be a vulnerary or some such,
            # but all cases in which this would matter have a proper weapon
            # there.
            self.select_new_item(job, item_id, at_least_one_weapon and i != 0)
            for i, item_id in enumerate(items)
        ]

    def select_new_item(self, job: JobData, item_id: int, force_weapon: bool):
        if item_id not in self.weapons_by_id:
            return item_id

        weapon_attrs: WeaponData = self.weapons_by_id[item_id]

        choices = [
            weap
            for weap in self.weapons_by_rank[weapon_attrs.rank]
            if weap.kind in job.usable_weapons
        ]

        if force_weapon:
            choices = [choice for choice in choices if choice.kind != WeaponKind.STAFF]

        return self.random.choice(choices).id

    def randomize_chapter_unit(self, data_offset: int, chapter_name: str) -> None:
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
        is_player = not bool(unit[2] & 0b0110)
        # Autolevel is LSB
        autolevel = unit[2] & 1
        inventory = unit[INVENTORY_INDEX : INVENTORY_INDEX + INVENTORY_SIZE]

        if char in self.recurring_characters:
            new_job = self.recurring_characters[char]
        else:
            new_job_pool = (
                self.promoted_jobs if job.is_promoted else self.unpromoted_jobs
            )
            new_job = self.random.choice(new_job_pool)

            self.recurring_characters[char] = new_job

        new_inventory = self.select_new_inventory(
            new_job, inventory, self.unit_must_fight(data_offset, char, chapter_name)
        )

        self.rom[data_offset + 1] = new_job.id
        for i, item_id in enumerate(new_inventory):
            self.rom[data_offset + INVENTORY_INDEX + i] = item_id

        # If an NPC isn't autoleveled, it's probably a boss or important NPC of
        # some kind, so we should force its weapon levels in the character
        # table.
        if not is_player and autolevel:
            for item_id in new_inventory:
                if item_id not in self.weapons_by_id:
                    continue
                boss_data_addr = CHARACTER_TABLE_OFFSET + char * 52
                weapon = self.weapons_by_id[item_id]
                boss_wrank_addr = boss_data_addr + 20 + weapon.kind
                rank = self.rom[boss_wrank_addr]
                self.rom[boss_wrank_addr] = max(rank, weapon.rank)

    def randomize_block(self, block: UnitBlock, chapter_name: str):
        for i in range(block.count):
            self.randomize_chapter_unit(
                block.base + i * CHAPTER_UNIT_SIZE, chapter_name=chapter_name
            )

    # TODO: logic
    #   - Valter must be holding a weapon
    #   - at least one of L'Arachel or Dozla must be able to fight
    #   - Nudge Cormag to 5,15 (pre) and 6,13 (post) in Eirika 13
    #   - Nudge Cormag to 11,12 in Ephraim 10
    #   - Nudge Tana to 0,5
    #   - Nudge the chapter 2 brigands
    #   - Saleh/Innes and Duessel/Knoll need to be able to fight in Ch15
    #   - Flying Duessel vs enemy archers in that Ephraim map may be unbeatable
    def apply_changes(self) -> None:
        for chapter_name, chapter in self.unit_blocks.items():
            for block in chapter:
                self.randomize_block(block, chapter_name=chapter_name)

        eirika_job = self.recurring_characters["Eirika"]

        # We give a random C-ranked weapon to Eirika to simulate the Rapier.
        new_rapier = self.select_new_item(eirika_job, STEEL_BLADE, False)
        self.rom[EIRIKA_RAPIER_OFFSET] = new_rapier
