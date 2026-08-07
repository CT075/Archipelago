# We deliberately do not import [random] directly to ensure that all random
# functions go through the multiworld rng seed.
from random import Random
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
import operator
import itertools
import functools
import logging

from typing import Any, Union, Optional, Callable, Iterable, Tuple

from .util import fetch_json, write_short_le, read_short_le, read_word_le, write_word_le

# XXX: most python lsps can't handle `from .constants import *`, so we have to
# specify these manually...
from .constants import (
    ROM_BASE_ADDRESS,
    CHAPTER_UNIT_SIZE,
    INVENTORY_INDEX,
    INVENTORY_SIZE,
    COORDS_INDEX,
    REDA_COUNT_INDEX,
    REDA_PTR_INDEX,
    CHARACTER_TABLE_BASE,
    CHARACTER_SIZE,
    CHARACTER_WRANK_OFFSET,
    CHARACTER_STATS_OFFSET,
    CHARACTER_GROWTHS_OFFSET,
    CHAR_ABILITY_4_OFFSET,
    JOB_TABLE_BASE,
    JOB_SIZE,
    JOB_STATS_OFFSET,
    JOB_CAPS_OFFSET,
    STATS_COUNT,
    EIRIKA,
    EIRIKA_LORD,
    EIRIKA_LOCK,
    EPHRAIM,
    EPHRAIM_LORD,
    EPHRAIM_LOCK,
    EIRIKA_RAPIER_OFFSET,
    ROSS_CH2_HP_OFFSET,
    ROSS_CH2_MAP_OFFSET,
    MOVEMENT_COST_TABLE_BASE,
    MOVEMENT_COST_ENTRY_SIZE,
    MOVEMENT_COST_ENTRY_COUNT,
    MOVEMENT_COST_SENTINEL,
    IMPORTANT_TERRAIN_TYPES,
    ITEM_TABLE_BASE,
    ITEM_SIZE,
    ITEM_ABILITY_1_INDEX,
    UNBREAKABLE_FLAG,
    LOCKPICK,
    CHEST_KEY_5,
    HOLY_WEAPON_IDS,
    MOUNTED_AID_CANTO_MASK,
    MOUNTED_MONSTERS,
    JOB_ABILITY_1_INDEX,
    CH15_AUTO_STEEL_SWORD,
    CH15_AUTO_STEEL_LANCE,
    TETHYS_EIRIKA,
    TETHYS_EPHRAIM,
    AI1_INDEX,
    INTERNAL_RANDO_CLASS_WEIGHTS_OFFS,
    INTERNAL_RANDO_CLASS_WEIGHT_ENTRY_SIZE,
    INTERNAL_RANDO_CLASS_WEIGHTS_COUNT,
    INTERNAL_RANDO_CLASS_WEIGHT_NUM_CLASSES,
    INTERNAL_RANDO_WEAPONS_OFFS,
    INTERNAL_RANDO_WEAPONS_ENTRY_SIZE,
    INTERNAL_RANDO_WEAPONS_MAX_CLASSES,
    INTERNAL_RANDO_WEAPON_TABLE_ROWS,
    FEMALE_JOBS,
    SONG_TABLE_BASE,
    SONG_SIZE,
    IS_PROMOTED,
    NOT_PROMOTED,
    DANCER_ID,
    MANAKETE_ID,
    DRACO_ZOMBIE_ID,
    THIEF_ID,
    CHARACTER_ORDER,
    VULNERARY_ID,
    ELIXER_ID,
    DRAGONSTONE_ID,
    BANDIT_AI,
    DELAYED_BANDIT_AI
)

from .connector_config import (
    FREE_UNIT_LOC
)


DEBUG = False


# CR cam: Maybe these should go into [constants]?

WEAPON_DATA = "data/weapondata.json"
JOB_DATA = "data/jobdata.json"
SONG_DATA = "data/songdata.json"
CHARACTERS = "data/characters.json"
CHARACTER_WRANKS = "data/character_wranks.json"
CHAPTER_UNIT_BLOCKS = "data/chapter_unit_blocks.json"
ALLY_UNIT_BLOCKS = "data/ally_unit_blocks.json"
MICRO_UNIT_BLOCKS = "data/micro_unit_blocks.json"
INTERNAL_RANDO_VALID_DISTRIBS = "data/internal_rando_distribs.json"


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

    # Currently, the names of blocks in `chapter_unit_blocks.json` are mostly
    # automatically generated from chapter event disassembly and are tagged
    # with any relevant information about the block.
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


class AllyBlock:
    name: str
    base: int
    count: int
    ids: set[int]

    # Currently, the names of blocks in `chapter_unit_blocks.json` are mostly
    # automatically generated from chapter event disassembly and are tagged
    # with any relevant information about the block.
    logic: defaultdict[Union[int, str], dict[str, Any]]

    def __init__(
        self,
        name: str,
        base: int,
        count: int,
        ids: set[int],
        logic: dict[str, dict[str, Any]],
    ):
        self.name = name
        self.base = base
        self.count = count
        self.ids = ids
        self.logic = defaultdict(
            dict, {int_if_possible(k): v for k, v in logic.items()}
        )


class GrowthRandoKind(IntEnum):
    NONE = 0
    REDISTRIBUTE = 1
    DELTA = 2
    FULL = 3


class MusicRandoKind(IntEnum):
    VANILLA = 0
    CONTEXT = 1
    CHAOS = 2


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
    def get_valid_names(cls) -> list[str]:
        return [
            "Sword",
            "Lance",
            "Axe",
            "Bow",
            "Staff",
            "Anima",
            "Light",
            "Dark",
            "Item",
            "Monster Weapon",
            "Ring",
            "Dragonstone",
        ]

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


class JobRace(IntEnum):
    ALL = 0
    HUMAN = 1
    MONSTER = 2



class JobType(IntEnum):
    ANY = 0
    RANGED = 1
    FLIER = 2
    LOCKPICK = 3
    HEALER = 4


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
            locks=obj.get("locks", set()),
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

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if not isinstance(other, JobData):
            return False
        return self.id == other.id


class CharacterStore:
    names_by_id: dict[int, str]
    ids_by_name: dict[str, list[int]]
    character_jobs: dict[str, JobData]
    character_tags: dict[str, set[str]]
    character_inventory: dict[str, list[int]]

    def __init__(self, char_data: dict[str, dict[str, Any]]):
        self.names_by_id = {}
        self.character_tags = dict()
        self.ids_by_name = dict()
        self.character_inventory = dict()

        for name, data in char_data.items():
            for i in data["ids"]:
                assert isinstance(i, int)
                self.names_by_id[i] = name

            # CR cam: figure out how to convince mypy that `data["tags"]` is
            # actually a list of strings
            self.character_tags[name] = set(data["tags"])
            self.ids_by_name[name] = data["ids"]

        self.character_jobs = {}

    def lookup_ids(self, char_name: str) -> Optional[list[int]]:
        if char_name not in self.ids_by_name:
            return None
        return self.ids_by_name[char_name]

    def lookup_jobs(self, char_name: str) -> Optional[list[int]]:
        if char_name not in self.ids_by_name:
            return None
        return self.character_jobs[char_name]

    def lookup_jobs_by_id(self, char_id: int) -> Optional[list[int]]:
        if char_id not in self.names_by_id:
            return None
        return self.lookup_jobs(self.names_by_id[char_id])

    def lookup_name(self, char_id: int) -> Optional[str]:
        if char_id not in self.names_by_id:
            return None
        return self.names_by_id[char_id]
     
    # these two could likely do the saftey checks faster / better but its still a improvement
    def set_inventory(self, char_id: int, invin: bytes) -> list[int]:
        if char_id not in self.names_by_id:
            return None
        name = self.names_by_id[char_id]
        if name not in self.character_inventory:
            self.character_inventory[name] = invin
        return self.character_inventory[name]

    def get_inventory(self, char_id: int):
        if char_id not in self.names_by_id:
            return None
        name = self.names_by_id[char_id]
        if name not in self.character_inventory:
            return None
        else:
            return self.character_inventory[name]

    def tags(self, char: Union[int, str]) -> Optional[set[str]]:
        if isinstance(char, int):
            if char not in self.names_by_id:
                return None
            name = self.names_by_id[char]
        else:
            name = char
        return self.character_tags[name]
    
    def FindUnitTagged(self, tag: str) -> Optional[str]:
        for x in CHARACTER_ORDER:
            holder= self.lookup_jobs_by_id(x).tags
            if  tag in holder :
                return self.lookup_name(x)
        return None


    def __setitem__(self, char: Union[int, str], job: JobData) -> None:
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

    def __contains__(self, char: Union[int, str]) -> bool:
        if isinstance(char, int):
            if char not in self.names_by_id:
                return False
            name = self.names_by_id[char]
        else:
            name = char

        return name in self.character_jobs


# CR cam: Eirika and Ephraim should be able to use their respective weapons if
# they get randomized into the right class.
def weapon_usable(weapon: WeaponData, job: JobData, logic: dict[str, Any]) -> bool:
    if any(lock not in job.tags for lock in weapon.locks):
        return False

    if "must_fight" in logic and weapon.kind in [
        WeaponKind.ITEM,
        WeaponKind.STAFF,
        WeaponKind.RING,
    ]:
        return False

    return True


# CR cam: ensure that all the progression weapons are usable
# CR-soon cam: This class does way too much. We should refactor this so things
# like `apply_5x_buffs` can happen external to this class.
class FE8Randomizer:
    unit_blocks: dict[str, list[UnitBlock]]
    ally_blocks: dict[str, list[AllyBlock]]
    weapons_by_id: dict[int, WeaponData]
    weapons_by_kind_rank: dict[WeaponKind, dict[WeaponRank, list[WeaponData]]]
    weapons_by_name: dict[str, WeaponData]
    character_store: CharacterStore
    jobs_by_id: dict[int, JobData]
    valid_distribs_by_row: dict[int, list[int]]
    jobs_pools: dict[bool, dict[JobRace, dict[JobType, list[JobData]]]]
    jobs_not_randomized: list[int]
    songs: dict[str, dict[int, str]]
    random: Random
    rom: bytearray
    config: dict[str, Any]
    ally_pick:bool
    micro: bool

    def __init__(self, rom: bytearray, random: Random, config: dict[str, Any], micro:bool = False):
        self.random = random
        self.rom = rom
        unit_blocks = fetch_json(CHAPTER_UNIT_BLOCKS)
        valid_distribs_by_row = fetch_json(INTERNAL_RANDO_VALID_DISTRIBS)
        item_data = fetch_json(WEAPON_DATA, object_hook=WeaponData.of_object)
        job_data = fetch_json(JOB_DATA,object_hook=JobData.of_object,)
        self.character_store = CharacterStore(fetch_json(CHARACTERS))
        songdata = fetch_json(SONG_DATA)
        self.jobs_not_randomized= [DRACO_ZOMBIE_ID]
        self.ally_pick = False
        self.config = config
        self.micro = micro
        
        if (self.micro):
            ally_blocks = fetch_json(MICRO_UNIT_BLOCKS)  
        else:
            ally_blocks = fetch_json(ALLY_UNIT_BLOCKS)
        
        self.character_wranks: dict[int, list[int]] = {
            int(k): v for k, v in fetch_json(CHARACTER_WRANKS).items()
        }

        self.unit_blocks = {
            name: [UnitBlock(**block) for block in blocks]
            for name, blocks in unit_blocks.items()
        }

        self.ally_blocks = {
            name: [AllyBlock(**block) for block in blocks]
            for name, blocks in ally_blocks.items()
        }

        self.valid_distribs_by_row = {
            int(k): v for k, v in valid_distribs_by_row.items()
        }

        self.weapons_by_id = {item.id: item for item in item_data}
        self.weapons_by_name = {item.name: item for item in item_data}
        self.jobs_by_id = {job.id: job for job in job_data}

        self.jobs_pools = defaultdict(list)
        for promo in [IS_PROMOTED, NOT_PROMOTED]:
            self.jobs_pools[promo] = defaultdict(list)
            for race in JobRace:
                self.jobs_pools[promo][race] = defaultdict(list)

        # sorting classes into the following class pools
        # 1. if they are promoted or not
        # 2. then, if they are a "human" or a "monster" class, as well as a "all" grouping
        # 3. then by tags, so is the class flying, lockpick or ranged atm but more can be added in time
        # This means there is a dedicated pool for promoted human fliers to make randomization faster
        for job in job_data:
            if "no_rando" not in job.tags and job.usable_weapons:
                if "monster" in job.tags:
                    Race = JobRace.MONSTER
                else:
                    Race = JobRace.HUMAN
                if "flying" in job.tags:
                    self.jobs_pools[job.is_promoted][Race][JobType.FLIER].append(job)
                    self.jobs_pools[job.is_promoted][JobRace.ALL][JobType.FLIER].append(
                        job
                    )
                elif "Lockpick" in job.tags:
                    self.jobs_pools[job.is_promoted][Race][JobType.LOCKPICK].append(job)
                    self.jobs_pools[job.is_promoted][JobRace.ALL][
                        JobType.LOCKPICK
                    ].append(job)
                if "ranged" in job.tags:
                    self.jobs_pools[job.is_promoted][Race][JobType.RANGED].append(job)
                    self.jobs_pools[job.is_promoted][JobRace.ALL][
                        JobType.RANGED
                    ].append(job)
                if "healer" in job.tags:
                    self.jobs_pools[job.is_promoted][Race][JobType.HEALER].append(job)
                    self.jobs_pools[job.is_promoted][JobRace.ALL][
                        JobType.HEALER
                    ].append(job)
                self.jobs_pools[job.is_promoted][JobRace.ALL][JobType.ANY].append(job)
                self.jobs_pools[job.is_promoted][Race][JobType.ANY].append(job)

        self.weapons_by_kind_rank = defaultdict(list)
        for kind in WeaponKind:
            self.weapons_by_kind_rank[kind] = defaultdict(list)

        # Weapons are given their own 2d dictionary so we can get a small weapon pool
        # Just find out what weapon levels the job has then what weapon rank you looking for

        for weap in self.weapons_by_id.values():
            self.weapons_by_kind_rank[weap.kind][weap.rank].append(weap)

        # Dark has no E-ranked weapons by default.
        self.weapons_by_kind_rank[WeaponKind.DARK][WeaponRank.E].append(
            self.weapons_by_name["Flux"]
        )

        # cam: Should we allow Lyon to become a monster?

        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.D].append(
            self.weapons_by_name["Fiery Fang"]
        )
        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.C].append(
            self.weapons_by_name["Fiery Fang"]
        )
        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.A].append(
            self.weapons_by_name["Hellfang"]
        )
        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.S].append(
            self.weapons_by_name["Hellfang"]
        )

        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.A].append(
            self.weapons_by_name["Fetid Claw"]
        )
        self.weapons_by_kind_rank[WeaponKind.MONSTER_WEAPON][WeaponRank.S].append(
            self.weapons_by_name["Fetid Claw"]
        )

        # CR-soon cam:
        # Darr: Dragon zombies experience the same problem. I've disabled them for now;
        # they only have one weapon and E-rank Wretched Air does not sound fun.
        #
        # Cam: What we need to do is prevent units from randomizing into Dracozombies
        # unless they have an A rank weapon. There are a few easy ways to hack that
        # in, but I'm going to punt on it for now because that's a bunch of design
        # decisions we can make later.


        self.songs = defaultdict(dict)
        for song in songdata:
            self.songs[song["category"]][int(song["id"], 16)] = song["name"]

    def job_valid(self, job: JobData, char: int, logic: dict[str, Any]) -> bool:
        # get list of tags that make the job invalid (notags)
        # the "no_" prefix adds the tag to the invalid tag list
        # "no_flying" makes any job with "flying" tag invalid
        notags = set()

        for x in logic:
            if x.startswith("no_") and logic[x]:
                notags.add(x.removeprefix("no_"))
        # job is invalid if it has any of the tags in notags
        if notags and notags & job.tags:
            return False
        if "must_fight" in logic and logic["must_fight"]:
            if "cannot_fight" in job.tags:
                return False
            if all(not wtype.damaging() for wtype in job.usable_weapons):
                return False

        return True

    def vanilla_highest_rank(self, char: int) -> int:
        """The highest weapon rank `char` had in the vanilla game, floored to E.

        The base patch zeroes the in-ROM character weapon-rank table, so these
        can't be read back from `self.rom`; they come from `character_wranks.json`
        (see `CHARACTER_WRANKS`). Characters with no entry (e.g. generic units)
        fall back to E.
        """
        row = self.character_wranks.get(char)
        return max(max(row) if row else 0, int(WeaponRank.E))

    def select_new_item(self, job: JobData, item_id: int, logic: dict[str, Any]) -> int:
        if item_id == LOCKPICK:
            if "lockpick" in job.tags or self.ally_pick == True:
                return LOCKPICK
            else:
                return CHEST_KEY_5

        if item_id == self.weapons_by_name["Reginleif"].id:
            # Ensure Ephraim gets a usable weapon to replace reginleif
            if self.config["enable_weapon_level_caps"]:
                max_rank = int(WeaponRank.C)
            else:
                max_rank = self.vanilla_highest_rank(EPHRAIM)
            return self.select_starting_weapon(job, max_rank)

        if item_id not in self.weapons_by_id:
            return item_id

        if job.id == DANCER_ID:
            return VULNERARY_ID
        
        weapon_attrs = self.weapons_by_id[item_id]

        # gets the weapon types equipable and adds them to the pool for the current weapon being changed
        useable = []
        for weapon_levels in job.usable_weapons:
            useable += self.weapons_by_kind_rank[weapon_levels][weapon_attrs.rank]

        choices = [weap for weap in useable if weapon_usable(weap, job, logic)]

        if not choices:
            import json

            logging.warning("LOGIC ERROR: no viable weapons, defaulting to E rank")
            logging.warning(f"  job: {job.name}")
            logging.warning(f"  rank: {weapon_attrs.rank}")
            logging.warning(f"  logic: {json.dumps(logic, indent=2)}")

            # gets the first type of equipable weapon
            first_type = next(iter(job.usable_weapons))
            choices = [
                weap
                for weap in self.weapons_by_kind_rank[WeaponRank.E][first_type]
                if weapon_usable(weap, job, dict())
            ]

            if not choices:
                logging.warning(
                    "LOGIC ERROR (2): still no viable weapons, defaulting to iron sword"
                )
                choices = [self.weapons_by_name["Iron Sword"]]

        return self.random.choice(choices).id

    def select_new_inventory(
        self, job: JobData, items: bytes, logic: dict[str, Any]
    ) -> list[int]:
        return [self.select_new_item(job, item_id, logic) for item_id in items]

    def select_starting_weapon(self, job: JobData, max_rank: int) -> int:
        """Pick a weapon `job` can actually use at the start, given a starting
        weapon rank of `max_rank` (a weapon-exp threshold). Used for starting
        equipment so a unit isn't handed a weapon its rank can't use.
        """
        candidates = [
            weap
            for weap in self.weapons_by_id.values()
            if weap.kind in job.usable_weapons and weapon_usable(weap, job, {})
        ]
        if not candidates:
            return self.weapons_by_name["Iron Sword"].id

        def usable(weap: WeaponData) -> bool:
            return weap.kind == WeaponKind.MONSTER_WEAPON or int(weap.rank) <= max_rank

        usable_weaps = [weap for weap in candidates if usable(weap)]
        if usable_weaps:
            best_rank = max(int(weap.rank) for weap in usable_weaps)
            pool = [weap for weap in usable_weaps if int(weap.rank) == best_rank]
        else:
            worst_rank = min(int(weap.rank) for weap in candidates)
            pool = [weap for weap in candidates if int(weap.rank) == worst_rank]
        return self.random.choice(pool).id

    def rewrite_coords(self, offset: int, x: int, y: int):
        old_coords = read_short_le(self.rom, offset)
        flags = old_coords & 0b1111000000000000
        new_coords = encode_unit_coords(x, y)
        write_short_le(self.rom, offset, new_coords | flags)

    def apply_nudges(self, data_offset: int, nudges: dict[str, list[int]]) -> None:
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

    def select_new_job(
        self,
        job: JobData,
        job_pool: Iterable[JobData],
        job_valid: Callable[[JobData], bool],
    ) -> JobData:
        choices = [job for job in job_pool if job_valid(job)]
        if not choices:
            logging.warning("LOGIC ERROR: no valid jobs")
            logging.warning(f"  original job: {job.name}")
            return job
        return self.random.choice(choices)

    def randomize_chapter_unit(
        self, data_offset: int, logic: dict[str, Any], Race: JobRace, not_force: bool = True
    ) -> None:
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

        # add character tags to logic
        ctags = self.character_store.tags(char)
        if not ctags:
            ctags = set()
        for t in ctags:
            if t not in logic:
                logic[t] = True

        AI_type = unit[17]

        if self.config["stop_bandit_mounted"] and not ("player" in logic and logic["player"]):
            if AI_type == BANDIT_AI or AI_type == DELAYED_BANDIT_AI:
                logic["no_flying"] = True
                logic["no_mounted"] = True

        no_store = "no_store" in logic and logic["no_store"]

        # config option for disabling unit randomization
        if ((not self.config["player_rando"] and "player" in logic and logic["player"])
            or (self.config["enemy_rando"] == 1 and "player"  not in logic)):
            if char not in self.character_store and not no_store:
                self.character_store[char] = job
            return
        
        if self.config["enemy_rando"]==5 and "player"  not in logic:
            if "monster" in job.tags:
                Race = JobRace.MONSTER
            else:
                Race = JobRace.HUMAN

        # stops any unit in jobs we dont want to be randomized
        # and saves them if they are a player unit
        if job_id in self.jobs_not_randomized:
            if "player" in logic and logic["player"]:
                self.character_store[char] = job
            return


        # Affiliation = bits 1,2; unit is player if they're unset
        is_player = not bool(unit[3] & 0b0110)
        # Autolevel is LSB
        autolevel = unit[3] & 1
        inventory = unit[INVENTORY_INDEX : INVENTORY_INDEX + INVENTORY_SIZE]

        if char in self.character_store and not_force and not no_store:
            new_job = self.character_store[char]
            # sets inventory from an earlier copy of yourself, if an inventory is stored
            # as cutscene units usually have 0 items not all are inventories are stored
            # as L'Arachel and other route splits have different inventories
            # so this keeps each route with their own inventories
            # marisa is only exception as there is no 0 inventory marisa so used ephraim route
            # so in Eirika route she gets a elixer instead of vulnerary  
            new_inventory = self.character_store.get_inventory(char)
            if new_inventory is None:
                new_inventory = self.select_new_inventory(new_job, inventory, logic)
        else:
            # Checks to see what job pool to use
            # Add other checks here for other pools added in later as a else if
            # could make pool intersections if you want to do like ranged fliers
            # but should never need to
            if "must_fly" in logic and logic["must_fly"]:
                Rules = JobType.FLIER
            elif "must_heal" in logic and logic["must_heal"]:
                Rules = JobType.HEALER
            elif "must_lockpick" in logic and logic["must_lockpick"]:
                Rules = JobType.LOCKPICK
            else:
                Rules = JobType.ANY
            if "must_dance" in logic and logic["must_dance"]:
                new_job= self.jobs_by_id [DANCER_ID]
            else:
                new_job = self.select_new_job(
                    job,
                    job_pool=self.jobs_pools[job.is_promoted][Race][Rules],
                    job_valid=lambda job: self.job_valid(job, char, logic),
                )
                new_inventory = self.select_new_inventory(new_job, inventory, logic)
            if not no_store:
                # likely could combine these 2 functions but might be read / stored in other places
                # only storing if you have 2 items as all ally units appear in cutscenes have 0 somewhere in the game
                # but Valter in prologue is his first apperance and only has 1 item then. 
                # so only saves units that have 2 or more items
                self.character_store[char] = new_job
                if new_inventory[1] != 0:
                    self.character_store.set_inventory(char, new_inventory)

        self.rom[data_offset + 1] = new_job.id
        for i, item_id in enumerate(new_inventory):
            self.rom[data_offset + INVENTORY_INDEX + i] = item_id

        # When weapon level caps are disabled, weapon ranks fall back to each
        # unit's own (vanilla) ranks. A player unit whose class was randomized
        # would otherwise keep ranks for its base class's weapon types
        if (
            is_player
            and self.config["player_rando"]
            and not self.config["enable_weapon_level_caps"]
        ):
            wrank_base = (
                CHARACTER_TABLE_BASE + char * CHARACTER_SIZE + CHARACTER_WRANK_OFFSET
            )
            # Build the unit's pool of actual vanilla ranks (nonzero, highest
            # first, keeping duplicates so the pool is distribution-weighted).
            row = self.character_wranks.get(char)
            pool = sorted((r for r in row if r > 0), reverse=True) if row else []
            if not pool:
                pool = [int(WeaponRank.E)]

            usable_kinds = sorted(int(kind) for kind in new_job.usable_weapons)
            n = len(usable_kinds)

            # Take the highest ranks first; once the whole pool is used, fill the
            # remaining slots by sampling from the pool at random (with replacement).
            if n <= len(pool):
                ranks = pool[:n]
            else:
                ranks = pool + [self.random.choice(pool) for _ in range(n - len(pool))]

            # Random rank -> weapon-type pairing.
            self.random.shuffle(ranks)

            usable_set = set(usable_kinds)
            for i in range(8):
                # Set unusuable weapon types to 0
                if i not in usable_set:
                    self.rom[wrank_base + i] = 0
            for kind, rank in zip(usable_kinds, ranks):
                # Dark has no E-rank weapon, so an E dark rank is unusable.
                if kind == WeaponKind.DARK:
                    rank = max(rank, int(WeaponRank.D))
                self.rom[wrank_base + kind] = rank

        if (
            "ai1_mod" in logic
            and self.rom[data_offset + AI1_INDEX] == logic["ai1_mod"]["from"]
        ):
            self.rom[data_offset + AI1_INDEX] = logic["ai1_mod"]["to"]

        # If an NPC isn't autoleveled, it's probably a boss or important NPC of
        # some kind, so we should force its weapon levels in the character
        # table.
        if not is_player and not autolevel and char in self.character_store and self.micro == False:
            for item_id in new_inventory:
                if item_id not in self.weapons_by_id:
                    continue
                boss_data_offs = CHARACTER_TABLE_BASE + char * CHARACTER_SIZE
                weapon = self.weapons_by_id[item_id]
                boss_wrank_offs = boss_data_offs + CHARACTER_WRANK_OFFSET + weapon.kind
                rank = self.rom[boss_wrank_offs]
                self.rom[boss_wrank_offs] = max(rank, weapon.rank)

    def randomize_block(self, block: UnitBlock, Race: JobRace):

        for i in range(block.count):
            offset = block.base + i * CHAPTER_UNIT_SIZE
            logic = block.logic[i]

            if "nudges" in logic:
                self.apply_nudges(offset, logic["nudges"])
            if "ignore" in logic and logic["ignore"]:
                continue
            # If this unit is tagged as a monster, its class gets selected by
            # the in-game randomizer, meaning we don't have to touch it.
            if "monster" in logic and logic["monster"]:
                continue
            self.randomize_chapter_unit(offset, logic, Race)

    def allies_logic_changes(self) -> None:
        '''
        For options that change logic of allies before randomization
        DO NOT DO ANY ROM BYTE MANIPULATION HERE AS WILL KILL WORLD GENERATION
        '''
        # if forcing a thief need a was to make sure we get a pick, why not use colms
        if self.config["force_thief"]:
            self.ally_pick = True
        # making sure that ch5x has at least 3 useable units to make it fun
        ephraim_group = [14, 15, 16, 33]
        for x in range(3):
            chosen = self.random.choice(ephraim_group)
            self.ally_blocks["Units"][chosen].logic[0]["must_fight"] = True
            ephraim_group.remove(chosen)

        # l'arachel's group gets the same thing but its mainly so Dozla can protect her
        larachel_group = [23, 24, 28]
        for x in range(2):
            chosen = self.random.choice(larachel_group)
            self.ally_blocks["Units"][chosen].logic[0]["must_fight"] = True
            larachel_group.remove(chosen)

        if not self.config["random_myrrh"]:
            self.jobs_not_randomized.append (MANAKETE_ID)
            
        if not self.config["random_tethys"]:
            self.jobs_not_randomized.append (DANCER_ID)

        # Setting to force Vanessa to be a flier
        if self.config["rescue_ross"] == 0:
            self.ally_blocks["Units"][5].logic[0]["must_fly"] = True

        if self.config["eirika_class"] == 0:
            self.ally_blocks["Units"][0].logic[0]["must_fight"] = True
        elif self.config["eirika_class"] > 0 and self.config["player_rando"]:
            # sets the class and invintory to be propagated
            self.character_store[EIRIKA] = self.jobs_by_id[self.config["eirika_class"]]
            self.character_store.set_inventory(EIRIKA, [0,0,0,0])
            # setting a varible that starts with "must_" so class reroller will skip her
            self.ally_blocks["Units"][0].logic[0]["must_pick"] = self.config["eirika_class"]

    def enemy_logic_changes(self) -> None:
        '''
        For options that change logic of enemy before randomization
        '''
        # we not a ally anymore
        self.ally_pick = False

        if self.config["no_rando_thief"]:
            self.jobs_not_randomized.append (THIEF_ID)

    def allies_logic_checks(self) -> None:
        '''
        For options that change logic of allies before after randomization
        should be used to confirm things output right
        DO NOT DO ANY ROM BYTE MANIPULATION HERE AS WILL KILL WORLD GENERATION
        '''
        if self.config["force_healer"] != 0:
            # checks to see if you have a healer and if you do gives them the tag
            if not (self.ally_check(self.config["force_healer"], "healer", "must_heal")):
                # if no healer gives the tag and re rolls them with it
                self.force_tag(self.config["force_healer"], "must_heal")

        if self.config["rescue_ross"] == 2:
            # checks to see if you have a flier and if you do gives them the tag
            if not (self.ally_check(6, "flying", "must_fly")):
                # if no flier gives the tag and re rolls them with it
                self.force_tag(6, "must_fly")

        if self.config["force_thief"]:
            # checks to see if you have a thief and if you do gives them the tag
            if not (self.ally_check(6, "lockpick", "must_lockpick")):
                # if no healer gives the tag and re rolls them with it
                self.force_tag(6, "must_lockpick")

        if self.config["force_dancer"]:
            # checks to see if you have a dancer and if you do gives them the tag
            if not (self.ally_check(33, "dancer", "must_dance")):
                # if no healer gives the tag and re rolls them with it
                self.force_tag(33, "must_dance")

    def ally_check(self, amount: int, needed_tag: str, given_logic: str) -> None:
        '''
        Checks to see if the needed tag is in the first amount of units
        then picks one and gives it the tag to ensure it always is there
        '''
        found = []
        count = 0
        for Units, block in self.ally_blocks.items():
            for unit in block:
                count += 1
                if count > amount:
                    break
                job = self.character_store.lookup_jobs_by_id(unit.ids)
                if needed_tag in job.tags:
                    found.append(unit)
        if found == []:
            return False
        else:
            self.random.choice(found).logic[0][given_logic] = True
            return True

    def force_tag(self, amount: int, given_logic: str) -> None:
        '''
        Checks the first amount of units and checks to see if they are allowed to re roll
        Picks one legal unit gives them the logic tag, and rerolls them
        '''
        potentials = []
        count = 0
        for group, block in self.ally_blocks.items():
            for unit in block:
                count += 1
                if count > amount:
                    break
                if self.force_legal(unit.logic, given_logic, self.character_store.lookup_jobs_by_id(unit.ids) ):
                    potentials.append(unit)
        choosen = self.random.choice(potentials)
        choosen.logic[0][given_logic] = True
        if not self.config["player_monster"]:
            Race = JobRace.HUMAN
        else:
            Race = JobRace.ALL
        self.randomize_chapter_unit(choosen.base, choosen.logic[0], Race, False)

    def force_legal(self, logic: dict[str, Any], given_logic, job: int):
        '''
        checks to see if a unit is legal to reroll
        '''

        for entry in logic[0]:
            if (
                entry.startswith("must_")
                and entry != given_logic
                and not (bool(entry == "must_fight") ^ bool(given_logic == "must_heal"))
                and not (bool(entry == "must_fight") ^ bool(given_logic == "must_dance")) 
                and job not in self.jobs_not_randomized
            ):
                return False
        return True

    # Randomize the classes and possible inventories for the game's internal
    # randomizer (used for skirmishes, tower/ruins, and the two random Wights
    # with Lyon for some reason).
    def randomize_monster_gen(self) -> None:
        class JobSet:
            promoted: set[JobData]
            unpromoted: set[JobData]

            def __init__(self):
                self.promoted = set()
                self.unpromoted = set()

            def add(self, job: JobData) -> None:
                (self.promoted if job.is_promoted else self.unpromoted).add(job)

            def __len__(self):
                return len(self.promoted) + len(self.unpromoted)

            def pools(self) -> Tuple[set[JobData], set[JobData]]:
                return self.unpromoted, self.promoted

            def iter(self):
                for j in self.unpromoted:
                    yield j
                for j in self.promoted:
                    yield j

        def job_valid_for_internal_rando(job: JobData) -> bool:
            # We disable mages because there aren't any entries for them in the
            # base weapon tables. Eventually we'll add them back in, but for
            # now we can just disable them.
            # CR-soon cam: Add these back in
            if any(
                map(
                    job.name.startswith,
                    (
                        # catches both regular Mages and "Mage Knight"
                        "Mage",
                        "Sage",
                        "Shaman",
                        "Druid",
                        "Priest",
                        "Cleric",
                        "Monk",
                        "Bishop",
                        "Troubadour",
                        "Valkyrie",
                        "Summoner",
                        "Necromancer",
                        "Pupil",
                        "Journeyman",
                        "Recruit",
                        "Dracozombie",
                    ),
                )
            ):
                return False

            return True

        # CR-soon cam: do this better
        weapon_tables = {
            (
                WeaponKind.of_str(ty) if ty in WeaponKind.get_valid_names() else ty,
                level,
            ): i
            for i, (ty, level) in enumerate(INTERNAL_RANDO_WEAPON_TABLE_ROWS)
        }
        jobset = JobSet()

        for i in range(INTERNAL_RANDO_CLASS_WEIGHTS_COUNT):
            offs = (
                INTERNAL_RANDO_CLASS_WEIGHTS_OFFS
                + i * INTERNAL_RANDO_CLASS_WEIGHT_ENTRY_SIZE
            )
            for j in range(INTERNAL_RANDO_CLASS_WEIGHT_NUM_CLASSES):
                job_id = self.rom[offs + j]
                if not job_id or job_id >= 255:
                    break
                if job_id == DRACO_ZOMBIE_ID:
                    continue
                job = self.jobs_by_id[job_id]
                unpromoted_pool, promoted_pool = (
                    jobset.pools()
                    # We _could_ repoint this and not need to check, but eh
                    if len(jobset) >= INTERNAL_RANDO_WEAPONS_MAX_CLASSES
                    else (
                        self.jobs_pools[NOT_PROMOTED][JobRace.ALL][JobType.ANY],
                        self.jobs_pools[IS_PROMOTED][JobRace.ALL][JobType.ANY],
                    )
                )
                new_job = self.select_new_job(
                    job,
                    promoted_pool if job.is_promoted else unpromoted_pool,
                    job_valid=job_valid_for_internal_rando,
                )
                self.rom[offs + j] = new_job.id
                jobset.add(new_job)

        # CR-someday cam: There is a lot of hardcoding going on here. It would
        # be nice to move some of the special-casing here to the data files.
        for i, job in enumerate(jobset.iter()):
            offs = INTERNAL_RANDO_WEAPONS_OFFS + i * INTERNAL_RANDO_WEAPONS_ENTRY_SIZE
            row1: Tuple[int, int, int, int, int]
            row1weights: Tuple[int, int, int, int, int]
            row1distrib: Tuple[int, int, int, int, int]
            if "Claw" in job.tags:
                pwr, distrib = {
                    "Revenant": (0, 1),
                    "Entombed": (1, 3),
                    "Bael": (2, 26),
                    "Elder Bael": (3, 27),
                }[job.name]
                idx = weapon_tables[("Claw", pwr)]
                row1 = (idx, 0, 0, 0, 0)
                row1weights = (100, 0, 0, 0, 0)
                row1distrib = (distrib, 0, 0, 0, 0)
            elif "Fang" in job.tags:
                pwr = 1 if job.is_promoted else 0
                idx = weapon_tables[("Fang", pwr)]
                row1 = (idx, 0, 0, 0, 0)
                row1weights = (
                    (25, 75, 0, 0, 0) if job.is_promoted else (75, 25, 0, 0, 0)
                )
                row1distrib = (13, 0, 0, 0, 0)
            elif "MonsterDark" in job.tags:
                match job.name:
                    case "Mogall":
                        idx = weapon_tables[("MonsterDark", 0)]
                        distrib_idx = 45
                    case "Arch Mogall":
                        idx = weapon_tables[("MonsterDark", 1)]
                        distrib_idx = 47
                    case "Gorgon":
                        idx = weapon_tables[("MonsterDark", 3)]
                        distrib_idx = 49
                    case other:
                        raise ValueError(
                            f"BUG: unhandled class {other} tagged as `MonsterDark`"
                        )
                row1 = (idx, 0, 0, 0, 0)
                row1weights = (100, 0, 0, 0, 0)
                row1distrib = (distrib_idx, 0, 0, 0, 0)
            elif len(job.usable_weapons) > 1:
                lo_pwr, mid_pwr, hi_pwr = (2, 3, 4) if job.is_promoted else (0, 1, 2)
                lo_kind1, lo_kind2 = self.random.sample(list(job.usable_weapons), k=2)
                lo_idx1 = weapon_tables[(lo_kind1, lo_pwr)]
                lo_idx2 = weapon_tables[(lo_kind2, lo_pwr)]
                hi_kind1, hi_kind2 = self.random.sample(list(job.usable_weapons), k=2)
                hi_idx1 = weapon_tables[(hi_kind1, hi_pwr)]
                hi_idx2 = weapon_tables[(hi_kind2, hi_pwr)]
                mid_kind = self.random.choice((lo_kind1, lo_kind2, hi_kind1, hi_kind2))
                mid_idx = weapon_tables[(mid_kind, mid_pwr)]
                row1 = (lo_idx1, hi_idx1, mid_idx, lo_idx2, hi_idx2)
                row1weights = (23, 15, 25, 22, 15)
                # doens't typecheck
                # row1distrib = tuple(
                #    self.random.choice(self.valid_distribs_by_row[row]) for row in row1
                # )
                row1distrib = (
                    self.random.choice(self.valid_distribs_by_row[row1[0]]),
                    self.random.choice(self.valid_distribs_by_row[row1[1]]),
                    self.random.choice(self.valid_distribs_by_row[row1[2]]),
                    self.random.choice(self.valid_distribs_by_row[row1[3]]),
                    self.random.choice(self.valid_distribs_by_row[row1[4]]),
                )
            else:
                kind = list(job.usable_weapons)[0]
                lo_pwr, mid_pwr, hi_pwr = (2, 3, 4) if job.is_promoted else (0, 1, 2)
                lo_idx = weapon_tables[(kind, lo_pwr)]
                mid_idx = weapon_tables[(kind, mid_pwr)]
                hi_idx = weapon_tables[(kind, hi_pwr)]
                row1 = (lo_idx, mid_idx, hi_idx, 0, 0)
                row1weights = (30, 35, 35, 0, 0)
                row1distrib = (
                    self.random.choice(self.valid_distribs_by_row[row1[0]]),
                    self.random.choice(self.valid_distribs_by_row[row1[1]]),
                    self.random.choice(self.valid_distribs_by_row[row1[2]]),
                    0,
                    0,
                )

            self.rom[offs] = job.id
            self.rom[offs + 1 : offs + 6] = bytes(row1)
            self.rom[offs + 11 : offs + 16] = bytes(row1weights)
            self.rom[offs + 21 : offs + 26] = bytes(row1distrib)

    def make_monsters_mounted(self) -> None:
        for job in MOUNTED_MONSTERS:
            entry = JOB_TABLE_BASE + job * JOB_SIZE
            self.rom[entry + JOB_ABILITY_1_INDEX] |= MOUNTED_AID_CANTO_MASK

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

    def normalize_genders(self) -> None:
        for fjob, mjob in FEMALE_JOBS:
            fjob_entry = JOB_TABLE_BASE + fjob * JOB_SIZE
            mjob_entry = JOB_TABLE_BASE + mjob * JOB_SIZE

            fjob_stats_base = fjob_entry + JOB_STATS_OFFSET
            mjob_stats_base = mjob_entry + JOB_STATS_OFFSET

            fjob_caps_base = fjob_entry + JOB_CAPS_OFFSET
            mjob_caps_base = mjob_entry + JOB_CAPS_OFFSET

            for i in range(STATS_COUNT + 1):
                self.rom[fjob_stats_base + i] = self.rom[mjob_stats_base + i]
                self.rom[fjob_caps_base + i] = self.rom[mjob_caps_base + i]

    def tweak_lords(self) -> None:
        for char, job, lock_mask in [
            (EIRIKA, EIRIKA_LORD, EIRIKA_LOCK),
            (EPHRAIM, EPHRAIM_LORD, EPHRAIM_LOCK),
        ]:
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
                self.rom[job_stats_base + i] -= new_personal_base

            ability_4_base = character_entry + CHAR_ABILITY_4_OFFSET
            self.rom[ability_4_base] |= lock_mask

    def fix_cutscenes(self) -> None:

        # We might not be able to rescue him so setting HP to 15
        # likely will give you a extra turn to reach him.
        self.rom[ROSS_CH2_HP_OFFSET] = 15

        # only need to adjust Eirika weapon if randomizing classes
        # if class's are random then Rapier should also be random
        if self.config["player_rando"]:
            # Eirika's Rapier is given in a cutscene at the start of the chapter,
            # rather than being in her inventory
            eirika_job = self.character_store["Eirika"]
            # Cap the starting weapon's rank to what she can actually use: 
            # party weapon ranks start at C when weapon level caps are enabled; 
            # otherwise her starting rank is her highest base-class rank 
            # (written into the character table during randomization).
            if self.config["enable_weapon_level_caps"]:
                max_rank = int(WeaponRank.C)
            else:
                max_rank = self.vanilla_highest_rank(EIRIKA)
            if eirika_job == DANCER_ID:
                new_rapier= VULNERARY_ID
            elif eirika_job == MANAKETE_ID:
                new_rapier= DRAGONSTONE_ID
            elif any(wkind != WeaponKind.STAFF for wkind in eirika_job.usable_weapons):
                new_rapier = self.select_starting_weapon(eirika_job, max_rank)
            else:
                healing = [
                    weap
                    for weap in (
                        self.weapons_by_name["Heal"],
                        self.weapons_by_name["Mend"],
                        self.weapons_by_name["Recover"],
                    )
                    if int(weap.rank) <= max_rank
                ] or [self.weapons_by_name["Heal"]]
                new_rapier = self.random.choice(healing).id
            self.rom[EIRIKA_RAPIER_OFFSET] = new_rapier

            # Eirika and Ephraim get automatic steels on rejoining in Ch15, which
            # need to be adjusted.
            if eirika_job == DANCER_ID:
                ch15_auto_steel_sword= ELIXER_ID
            elif eirika_job == MANAKETE_ID:
                ch15_auto_steel_sword= DRAGONSTONE_ID
            else:
                ch15_auto_steel_sword = self.select_new_item(
                eirika_job, self.weapons_by_name["Steel Sword"].id, {}
            )
            self.rom[CH15_AUTO_STEEL_SWORD] = ch15_auto_steel_sword

            ephraim_job = self.character_store["Ephraim"]

            if ephraim_job == DANCER_ID:
                ch15_auto_steel_lance= ELIXER_ID
            elif ephraim_job == MANAKETE_ID:
                ch15_auto_steel_lance= DRAGONSTONE_ID
            else:
                ch15_auto_steel_lance = self.select_new_item(
                ephraim_job, self.weapons_by_name["Steel Lance"].id, {}
            )
            self.rom[CH15_AUTO_STEEL_LANCE] = ch15_auto_steel_lance

            tethys_job = self.character_store["Tethys"]
            if tethys_job != DANCER_ID:
                tethys_weapon = self.select_new_item(
                    tethys_job, self.weapons_by_name["Steel Lance"].id, {}
                )
                self.rom[TETHYS_EPHRAIM] = tethys_weapon
                self.rom[TETHYS_EIRIKA] = tethys_weapon
            

    # TODO: logic
    #   - Flying Duessel vs enemy archers in Ephraim 10 may be unbeatable
    def clear_weapon_ranks(self) -> None:
        for ids in self.character_store.ids_by_name.values():
            for char_id in ids:
                wrank_base = CHARACTER_TABLE_BASE + CHARACTER_SIZE * char_id + CHARACTER_WRANK_OFFSET
                for i in range(8):
                    self.rom[wrank_base + i] = 0

    def randomize_units(self) -> None:

        Race = JobRace.ALL
        if self.config["enemy_rando"] == 3:
            Race = JobRace.MONSTER
        elif self.config["enemy_rando"] == 4:
            Race = JobRace.HUMAN

        for chapter_name, chapter in self.unit_blocks.items():
            for block in chapter:
                try:
                    self.randomize_block(block, Race)
                except (ValueError, IndexError) as e:
                    logging.error("crash dump:")
                    logging.error(f"  block_data: {chapter_name}, {block.name}")
                    logging.error(f"  {e}")
                    raise

    def randomize_allies(self) -> None:
        '''
        Where all playable units are randomized
        '''
        # Checks to see if monsters are in logic or if it should just use humans
        if not self.config["player_monster"]:
            Race = JobRace.HUMAN
        else:
            Race = JobRace.ALL
        for chapter_name, chapter in self.ally_blocks.items():
            for block in chapter:
                try:
                    self.randomize_block(block, Race)
                except (ValueError, IndexError) as e:
                    logging.error("crash dump:")
                    logging.error(f"  block_data: {chapter_name}, {block.name}")
                    logging.error(f"  {e}")
                    raise

    def apply_base_changes(self) -> None:
        self.free_deploys()
        self.fix_movement_costs()
        self.fix_cutscenes()
        self.tweak_lords()
        self.make_monsters_mounted()

    def free_deploys(self) -> None:
        '''
        For units that always get deployed even though unitsanity
        '''
        if self.config["first_healer_deployment"]:
            self.make_deploy(self.character_store.FindUnitTagged("healer"))
        if self.config["first_thief_deployment"]:
            self.make_deploy(self.character_store.FindUnitTagged("lockpick"))

    def make_deploy(self, unit:str):
        '''
        Sets the units flag to true that lets them skip the item check
        '''
        if unit != None:
            self.rom[FREE_UNIT_LOC.get (unit)] = 1

    def apply_5x_buffs(self) -> None:
        for char in ["Ephraim", "Forde", "Kyle"]:
            ids = self.character_store.lookup_ids(char)
            if ids is None:
                logging.error(f"Error: apply_5x_buffs: Unable to lookup ids for {char}")
                continue
            for char_id in ids:
                char_base = CHARACTER_TABLE_BASE + CHARACTER_SIZE * char_id
                stats_base = char_base + CHARACTER_STATS_OFFSET
                for i in range(STATS_COUNT):
                    self.rom[stats_base + i] += 2
                    
    def map_edit(self) -> None:
        # make path to ross
        # tile  1
        self.rom[ROSS_CH2_MAP_OFFSET] = 156
        self.rom[ROSS_CH2_MAP_OFFSET + 1] = 11
        # tile 2
        self.rom[ROSS_CH2_MAP_OFFSET + 2] = 168
        self.rom[ROSS_CH2_MAP_OFFSET + 3] = 1
        # make map look nicer
        self.rom[ROSS_CH2_MAP_OFFSET + 31] = 196

    def apply_infinite_holy_weapons(self) -> None:
        for weapon_id in HOLY_WEAPON_IDS:
            weapon_base = ITEM_TABLE_BASE + weapon_id * ITEM_SIZE
            ability_1_base = weapon_base + ITEM_ABILITY_1_INDEX
            self.rom[ability_1_base] |= UNBREAKABLE_FLAG

    def redistribute_growths(self, total: int) -> list[int]:
        cuts = sorted(self.random.sample(range(1, total), STATS_COUNT))
        result = []
        overflow = 0
        for st, end in zip([0] + cuts, cuts + [total]):
            growth = end - st
            if growth > 255:
                result.append(255)
                overflow += growth - 255
            else:
                result.append(growth)
        while overflow > 0:
            available_indices = [i for i, g in enumerate(result) if g < 255]
            if not available_indices:
                break
            i = self.random.choice(available_indices)
            result[i] += overflow
            overflow = 0
            if result[i] > 255:
                overflow = result[i] - 255
                result[i] = 255
        return result

    def randomize_growths(self, kind: GrowthRandoKind, grmin: int, grmax: int) -> None:
        if grmin > grmax:
            grmin, grmax = grmax, grmin

        player_ids: Iterable[int] = itertools.chain.from_iterable(
            ids
            for ids in (
                self.character_store.lookup_ids(char)
                for char in self.character_store.character_tags
                if "player" in self.character_store.character_tags[char]
            )
            if ids is not None
        )

        def roll_delta() -> int:
            delta = self.random.randint(grmin, grmax)
            direction = self.random.choice([-1, 1])
            return delta * direction

        for char_id in player_ids:
            char_base = CHARACTER_TABLE_BASE + CHARACTER_SIZE * char_id
            growths_base = char_base + CHARACTER_GROWTHS_OFFSET
            growths = list(self.rom[growths_base : growths_base + STATS_COUNT + 1])
            new_growths: list[int]
            match kind:
                case GrowthRandoKind.NONE:
                    return
                case GrowthRandoKind.REDISTRIBUTE:
                    total = sum(growths) + roll_delta()
                    new_growths = self.redistribute_growths(total)
                case GrowthRandoKind.DELTA:
                    new_growths = [max(growth + roll_delta(), 0) for growth in growths]
                case GrowthRandoKind.FULL:
                    new_growths = [self.random.randint(grmin, grmax) for _ in growths]

            for i in range(STATS_COUNT + 1):
                self.rom[growths_base + i] = max(min(255, new_growths[i]), 0)

    def generate_swaps(
        self, songs: dict[int, str]
    ) -> list[Tuple[Tuple[int, str], Tuple[int, str]]]:
        ids = list(songs.items())
        return list(zip(ids, self.random.sample(ids, k=len(ids))))

    def randomize_music(self, kind: MusicRandoKind) -> None:
        swaps: list[Tuple[Tuple[int, str], Tuple[int, str]]]
        match kind:
            case MusicRandoKind.VANILLA:
                return
            case MusicRandoKind.CONTEXT:
                swaps = list(
                    itertools.chain.from_iterable(
                        self.generate_swaps(songs)
                        for (_ctx, songs) in self.songs.items()
                    )
                )
            case MusicRandoKind.CHAOS:
                swaps = self.generate_swaps(
                    functools.reduce(operator.or_, self.songs.values())
                )

        logging.debug("Music rando song swaps:")
        ptrs: list[Tuple[int, int]] = []
        for (baseid, basename), (newid, newname) in swaps:
            logging.debug(f"  {basename} ({hex(baseid)}) -> {newname} ({hex(newid)})")
            ptrs.append(
                (baseid, read_word_le(self.rom, SONG_TABLE_BASE + newid * SONG_SIZE))
            )

        for id, ptr in ptrs:
            write_word_le(self.rom, SONG_TABLE_BASE + id * SONG_SIZE, ptr)
