CLIENT_TITLE = "FE8Client"
FE8_NAME = "Fire Emblem Sacred Stones"

FE8_ID_PREFIX = 0xFE8_000
NUM_LEVELCAPS: int = (40 - 10) // 5

HOLY_WEAPONS = {
    "Sieglinde": "Sword",
    "Siegmund": "Lance",
    "Gleipnir": "Dark",
    "Garm": "Axe",
    "Nidhogg": "Bow",
    "Vidofnir": "Lance",
    "Excalibur": "Anima",
    "Audhulma": "Sword",
    "Ivaldi": "Light",
    "Latona": "Staff",
}

WEAPON_TYPES = ["Sword", "Lance", "Axe", "Bow", "Anima", "Light", "Dark", "Staff"]
NUM_WEAPON_LEVELS = 3

FILLER_ITEMS = [
    "AngelicRobe",
    "EnergyRing",
    "SecretBook",
    "Speedwings",
    "GoddessIcon",
    "DragonShield",
    "Talisman",
    "BodyRing",
    "Boots",
    "KnightCrest",
    "HeroCrest",
    "OrionsBolt",
    "GuidingRing",
    "ElysianWhip",
    "OceanSeal",
    "MasterSeal",
]

FEMALE_JOBS = [
    (0x06, 0x05),  # Cavalier
    (0x08, 0x07),  # Paladin
    (0x0A, 0x09),  # Armour Knight
    (0x0C, 0x0B),  # General
    (0x10, 0x0F),  # Mercenary
    (0x12, 0x11),  # Hero
    (0x14, 0x13),  # Myrmidon
    (0x16, 0x15),  # Swordmaster
    (0x18, 0x17),  # Assassin
    (0x1A, 0x19),  # Archer
    (0x1C, 0x1B),  # Sniper
    (0x1E, 0x1D),  # Ranger
    (0x20, 0x1F),  # Wyvern Rider
    (0x22, 0x21),  # Wyvern Lord
    (0x24, 0x23),  # Wyvern Knight
    (0x26, 0x25),  # Mage
    (0x28, 0x27),  # Sage
    (0x2A, 0x29),  # Mage Knight
    (0x2C, 0x2B),  # Bishop
    (0x2E, 0x2D),  # Shaman
    (0x30, 0x2F),  # Druid
    (0x32, 0x31),  # Summoner
    (0x36, 0x35),  # Great Knight
]

ROM_BASE_ADDRESS = 0x08000000
ROM_NAME_ADDR = 0x080000A0

PROC_SIZE = 0x6C
PROC_POOL_ADDR = 0x02024E68
TOTAL_NUM_PROCS = 0x40

# These are literal addresses including the ROM offset because we compare
# against them, rather than reading or writing.
WM_PROC_ADDRESS = 0x08A3EE74
PREP_SCREEN_PROC_ADDRESS = 0x0859DBBC
E_PLAYERPHASE_PROC_ADDRESS = 0x0859AAD8

LOCKPICK = 0x6B
CHEST_KEY_5 = 0x79

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
CHARACTER_GROWTHS_OFFSET = 28
CHAR_ABILITY_4_OFFSET = 43

JOB_TABLE_BASE = 0x807110
JOB_SIZE = 84
JOB_STATS_OFFSET = 11
JOB_CAPS_OFFSET = 19
JOB_ABILITY_1_INDEX = 40

SONG_TABLE_BASE = 0x224470
SONG_SIZE = 8

STATS_COUNT = 6  # HP, Str, Skl, Spd, Def, Res (don't need Lck)

MOUNTED_AID_CANTO_MASK = 3
MOUNTED_MONSTERS = [
    0x5D,  # Tarvos
    0x5E,  # Maelduin
    0x5F,  # Mogall
    0x60,  # Mogall
    0x63,  # Gargoyle
    0x64,  # Deathgoyle
]

EIRIKA = 1
EIRIKA_LORD = 2
EIRIKA_LOCK = 1 << 4
EPHRAIM = 15
EPHRAIM_LORD = 1
EPHRAIM_LOCK = 1 << 5

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

ITEM_TABLE_BASE = 0x809B10
ITEM_SIZE = 36
ITEM_ABILITY_1_INDEX = 8
UNBREAKABLE_FLAG = 1 << 3

HOLY_WEAPON_IDS = [
    0x85,  # Sieglinde
    0x92,  # Siegmund
    0x4A,  # Gleipnir
    0x93,  # Garm
    0x94,  # Nidhogg
    0x8E,  # Vidofnir
    0x3E,  # Excalibur
    0x91,  # Audhulma
    0x87,  # Ivaldi
]
DRAGONSTONE_ID = 170

CH15_AUTO_STEEL_LANCE = 0x086664
CH15_AUTO_STEEL_SWORD = 0x086674
TETHYS_EIRIKA= 0x8B89C3
TETHYS_EPHRAIM=0x8C5296

AI1_INDEX = 0x10
AI1_IGNORE_LIST_12 = 0x5A8A24

INTERNAL_RANDO_CLASS_WEIGHTS_OFFS = 0x8D2060
INTERNAL_RANDO_CLASS_WEIGHT_ENTRY_SIZE = 12
INTERNAL_RANDO_CLASS_WEIGHTS_COUNT = 30
INTERNAL_RANDO_CLASS_WEIGHT_NUM_CLASSES = 5
INTERNAL_RANDO_CLASS_OFFS = 0x8D2440
INTERNAL_RANDO_CLASS_ENTRY_SIZE = 0x20
INTERNAL_RANDO_CLASS_NUM_ITEMS = 5
INTERNAL_RANDO_CLASS_MAX_CLASSES = 22
INTERNAL_RANDO_WEAPON_OFFS = 0x8D21C8
INTERNAL_RANDO_WEAPON_ENTRY_SIZE = 5

IS_PROMOTED = True
NOT_PROMOTED = False

DANCER_ID = 77
MANAKETE_ID = 59
DRACO_ZOMBIE_ID = 101
THIEF_ID = 13

VULNERARY_ID = 108
ELIXER_ID = 109

ROSS_CH2_MAP_OFFSET =0x1B74CD

BANDIT_AI = 4
DELAYED_BANDIT_AI = 17


# CR-soon cam: This is stretching the definition of a "constant" and should
# probably go into a data file instead
INTERNAL_RANDO_WEAPON_TABLE_ROWS = [
    ("None", -1),
    ("Sword", 0),
    ("Sword", 1),
    ("Sword", 3),
    ("Sword", 2),
    ("Sword", 4),
    ("Lance", 0),
    ("Lance", 1),
    ("Lance", 3),
    ("Lance", 2),
    ("Lance", 4),
    ("Axe", 0),
    ("Axe", 1),
    ("Axe", 3),
    ("Axe", 2),
    ("Axe", 4),
    ("Bow", 0),
    ("Bow", 1),
    ("Bow", 3),
    ("Bow", 2),
    ("Bow", 4),
    ("Claw", 0),
    ("Claw", 1),
    ("Claw", 2),
    ("Claw", 3),
    ("MonsterDark", 0),
    ("MonsterDark", 1),
    ("Fang", 0),
    ("Fang", 1),
    ("MonsterDark", 3),
    ("Breath", 0),
    ("Item", 0),
    ("Item", 1),
    ("Item", 2),
    ("Item", 3),
    ("Item", 4),
    ("Item", 5),
    ("Item", 6),
    ("Item", 7),
    ("Anima", 0),
    ("Anima", 1),
    ("Anima", 2),
    ("Item", 8),
    ("Item", 9),
    ("Item", 10),
    ("Item", 11),
    ("Item", 12),
    ("Item", 13),
    ("Item", 14),
    ("Item", 15),
]

CHARACTER_ORDER=[
    1,
    2,
    4,
    3,
    5,
    6,
    7,
    10,
    8,
    9,
    19,
    12,
    13,
    32,
    15,
    16,
    17,
    34,
    18,
    21,
    20,
    11,
    22,
    26,
    25,
    23,
    24,
    14,
    28,
    29,
    31,
    30,
    33,
    36
]

DEPLOY_EARLY_UNITS = frozenset(
    {
        "Seth",
        "Franz",
        "Gilliam",
        "Vanessa",
        "Moulder",
        "Ross",
        "Garcia",
        "Neimi",
        "Colm",
        "Artur",
        "Lute",
        "Natasha",
        "Joshua",
    }
)
DEPLOY_MID_UNITS = frozenset(
    {
        "Forde",
        "Kyle",
        "Tana",
        "Amelia",
        "Innes",
        "Gerik",
        "Tethys",
        "Marisa",
        "L'Arachel",
        "Dozla",
        "Saleh",
        "Ewan",
        "Cormag",
        "Rennac",
        "Duessel",
        "Knoll",
    }
)
# late tier: Myrrh, Syrene

MICRO_ROM = b'\x01\x02\x00\x08\x48\x01\x00\x01\xF4\x3B\x8B\x08\x6C\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x02\x07\x00\x08\x4D\x02\x00\x06\xC4\x3B\x8B\x08\x03\x17\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x04\x05\x01\x08\x05\x00\x00\x01\x58\x40\x8B\x08\x01\x14\x6C\x6C\x00\x00\x00\x00'
MICRO_ROM += b'\x03\x09\x00\x20\x06\x00\x00\x01\x60\x40\x8B\x08\x14\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x05\x45\x00\x18\x01\x00\x00\x01\x64\x42\x8B\x08\x4B\x6C\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x06\x48\x00\x08\x40\x00\x00\x01\x9C\x42\x8B\x08\x15\x1C\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x07\x3D\x00\x0A\x8B\x00\x00\x01\xA4\x42\x8B\x08\x2C\x6C\x00\x00\x00\x0A\x00\x00'
MICRO_ROM += b'\x0A\x3F\x00\x22\x8B\x00\x00\x01\xAC\x42\x8B\x08\x1F\x28\x6C\x00\x00\x03\x00\x00'
MICRO_ROM += b'\x08\x1A\x00\x08\x80\x02\x00\x01\x04\x45\x8B\x08\x2D\x6C\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x09\x0D\x00\x12\x40\x01\x00\x01\x6C\x45\x8B\x08\x01\x6B\x6C\x00\x06\x05\x08\x00'
MICRO_ROM += b'\x13\x44\x00\x10\x89\x02\x00\x03\x74\x48\x8B\x08\x3F\x6C\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x0C\x26\x00\x08\xC1\x02\x00\x01\x8C\x48\x8B\x08\x38\x6C\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x0D\x4A\x00\x08\x0A\x00\x00\x01\x18\x56\x8B\x08\x4C\x6C\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x20\x13\x00\x2C\x8C\x01\x00\x01\xF0\x55\x8B\x08\x0D\x00\x00\x00\x07\x03\x09\x00'
MICRO_ROM += b'\x0F\x01\x00\x20\x81\x04\x00\x01\x2C\x5A\x8B\x08\x78\x16\x6D\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x10\x05\x00\x30\x83\x04\x00\x01\x34\x5A\x8B\x08\x03\x1C\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x11\x05\x00\x28\x80\x04\x00\x01\x3C\x5A\x8B\x08\x01\x16\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x22\x48\x00\x08\x80\x00\x00\x01\x8C\x83\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x12\x47\x00\x25\x11\x03\x00\x00\x00\x00\x00\x00\x15\x6C\x5E\x00\x00\x00\x09\x00'
MICRO_ROM += b'\x15\x4D\x00\x08\x00\x00\x00\x05\xFC\x97\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x14\x0F\x00\x52\x44\x04\x00\x00\x00\x00\x00\x00\x06\x6C\x64\x00\x00\x03\x03\x00'
MICRO_ROM += b'\x0B\x1B\x00\x08\x08\x01\x00\x02\x98\xB9\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x16\x14\x00\x2C\xCD\x00\x00\x00\x00\x00\x00\x00\x0C\x6D\x00\x00\x00\x03\x09\x00'
MICRO_ROM += b'\x1A\x43\x19\x0A\x4C\x04\x00\x01\x84\x97\x8B\x08\x86\x6D\x00\x00\x00\x03\x00\x00'
MICRO_ROM += b'\x19\x4B\x00\x0B\x12\x00\x00\x01\xAC\x7B\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x17\x27\x00\x08\x40\x05\x00\x01\xC8\xA0\x8B\x08\x3A\x39\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x18\x3E\x01\x08\x4C\x01\x00\x03\xF0\xA0\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x0E\x1F\x00\x50\x86\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x1C\x33\x00\x0B\x13\x00\x00\x01\xBC\x7B\x8B\x08\x00\x00\x00\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x1D\x35\x00\x2B\x4B\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x03\x09\x20'
MICRO_ROM += b'\x1F\x2D\x00\x51\xC0\x04\x00\x01\x60\xC5\x8B\x08\x45\x47\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x1E\x3C\x00\x08\xD0\x05\x00\x00\x00\x00\x00\x00\xAA\x6D\x6C\x00\x00\x00\x00\x00'
MICRO_ROM += b'\x21\x49\x00\x0A\x4D\x01\x00\x03\x00\xDD\x8B\x08\x17\x1C\x00\x00\x03\x03\x00\x00'
MICRO_ROM += b'\x42\x07\x00\x18\x80\x04\x00\x01\x44\x5A\x8B\x08\x04\x16\x6C\x00\x00\x00\x00\x00'
