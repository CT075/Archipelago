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

ROM_BASE_ADDRESS = 0x08000000

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
CHAR_ABILITY_4_OFFSET = 43

JOB_TABLE_BASE = 0x807110
JOB_SIZE = 84
JOB_STATS_OFFSET = 11

STATS_COUNT = 6  # HP, Str, Skl, Spd, Def, Res (don't need Lck)

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
