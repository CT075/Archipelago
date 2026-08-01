from dataclasses import dataclass
from typing import List, TYPE_CHECKING, Dict, Any

from Options import Choice, Range, Toggle, PerGameCommonOptions, OptionGroup

def create_option_groups() -> List[OptionGroup]:
    option_group_list: List[OptionGroup] = []
    for name, options in FE8_option_groups.items():
        option_group_list.append(OptionGroup(name=name, options=options))

    return option_group_list

def round_up_to(x, mod):
    return ((x + mod - 1) // mod) * mod


class PlayerRando(Toggle):
    """
    If enabled, playable units will be randomzied
    """

    display_name = "Randomize Player Units"
    default = 1


class PlayerMonsters(Toggle):
    """
    Allow playable units to randomize into monsters when enabled
    """

    display_name = "Enable Playable Monsters"
    default = 1

class EnemyRando(Choice):
    """
    How would you like enemy's to be randomzied into
    1. No rando
    2. All classes
    3. Monsters only
    4. Humans only
    5. Humans into humans / Monsters into monsters
    """

    display_name = "Enemy Randomization Results"
    option_No_rando = 1
    option_All_classes = 2
    option_Monster_only = 3
    option_Human_only = 4
    option_Same_race = 5
    default = 2



class RandomTethys(Toggle):
    """
    Allow Tethys to be randomized
    """

    display_name = "Randomize Tethys"
    default = 0

class RandomMyrrh(Toggle):
    """
    Allow Myrrh to be randomized
    """

    display_name = "Randomize Myrrh"
    default = 0


class SuperDemonKing(Toggle):
    """
    Buffs the final boss to have higher stats and to take less damage from
    non-holy weapons.

    If enabled, it is strongly recommended to set `Required Usable Holy
    Weapons` to at least 2.
    """

    display_name = "Super Demon King"


class SmoothLevelCapProgression(Toggle):
    """
    Tie level cap progression roughly against story progression.

    This may cause problems if enabled when `Minimum Endgame Level Cap` is
    below 30.
    """

    display_name = "Smooth Level Caps"
    default = 1


class EnableLevelCaps(Toggle):
    """
    If enabled, your party's level cap starts low and is raised by "Progressive
    Level Cap" items shuffled into the item pool.

    If disabled, those items are left out of the pool and your party is uncapped
    from the start (up to the game's normal maximum). Note that `Minimum Endgame
    Level Cap` and `Smooth Level Caps` have no effect when this is disabled.
    """

    display_name = "Enable Level Caps"
    default = 1


class EnableWeaponLevelCaps(Toggle):
    """
    If enabled, your party's weapon ranks start low and are raised by
    "Progressive Weapon Level" items shuffled into the item pool.

    If disabled, those items are left out of the pool and weapon levels
    work like the base game
    """

    display_name = "Enable Weapon Level Caps"
    default = 1


class MinimumEndgameLevelCapRange(Range):
    """
    Attempt to place level uncaps such that your level cap will be at least
    this high by the time you reach the final boss. Note that this is your
    level *cap*, not your actual party level. Rounds to the next highest
    multiple of 5. Promoted level caps are treated as 20+n (so promoted level
    10 would be level 30).

    Beware of setting this too low, especially if Super Demon King is enabled.
    Setting this too high may lead to level cap checks being placed late into
    progression if `Smooth Level Caps` is unset.
    """

    display_name = "Minimum Endgame Level Cap"
    range_start = 10
    range_end = 40
    default = 40

    def __init__(self, value: int):
        super().__init__(round_up_to(value, 5))


class MinimumUsableHolyWeapons(Range):
    """
    The expected number of holy weapons necessary to defeat the final boss.

    If nonzero, attempt to place holy weapons *and* the weapon rank boosts
    necessary to use them such that `n` holy weapons are accessible before the
    final boss. See also `Exclude Latona from holy weapon pool`.
    """

    display_name = "Required Usable Holy Weapons"
    range_start = 0
    range_end = 9
    default = 0


class ExcludeLatona(Toggle):
    """
    If enabled, don't count Latona as a holy weapon for the sake of
    `Required Usable Holy Weapons`.
    """

    display_name = "Exclude Latona from holy weapon pool"
    default = 1


# Cam: Should we make this a sliding scale?
class Easier5x(Toggle):
    """
    Give Ephraim, Forde and Kyle extra base stats. This is recommended to make
    chapter 5x significantly less of a slog.
    """

    display_name = "Buff Ephraim's party for chapter 5x"
    default = 1

class ForceHealer(Range):
    """
    Will make sure you have a healer in the first X amount of units.
    This is done using Eirika route recruitment order.
    """

    display_name = "Guarantee a healer"
    range_start = 0
    range_end = 34
    default = 0

class ForceThief(Toggle):
    """
    Will make sure you have a thief in the first 6 amount of units.
    (Colm or before)
    """

    display_name = "Guarantee a thief"
    default = 0

class ForceDancer(Toggle):
    """
    Will make sure you have a dancer as one of your units.
    """

    display_name = "Guarantee a dancer"
    default = 0


class UnbreakableRegalia(Toggle):
    """
    Make all holy weapons other than Latona unbreakable.
    """

    display_name = "Unbreakable Regalia"
    default = 0


class EnableRecruitChecks(Toggle):
    """
    Make each character recruitment a check. Adds 31 locations (one per
    recruitable unit) and adds deploy permit items to the item pool, so
    units must be unlocked before they can be deployed on the prep screen.
    """

    display_name = "Enable recruit checks"
    default = 1


class ProgressiveSethDeployment(Toggle):
    """
    Requires Enable recruit checks.

    When enabled, Seth's deploy permit is replaced by 4 progressive items
    (denoted by the letters S, E, T, and H). Each received item reveals a hint and the
    fourth grants Seth's deploy permit. When disabled, a single Deploy Seth
    item is used instead.
    """

    display_name = "Progressive Seth deployment"
    default = 0

class FirstHealerDeployment(Toggle):
    """
    Requires Enable recruit checks.

    When enabled, your first healer will not need a item to be deployed.
    This is done using Eirika route recruitment order.
    """

    display_name = "First healer deployment"
    default = 0

class FirstThiefDeployment(Toggle):
    """
    Requires Enable recruit checks.

    When enabled, your first thief will not need a item to be deployed.
    This is done using Eirika route recruitment order.
    """

    display_name = "First thief deployment"
    default = 0

class RescueRoss(Choice):
    """
    How would you like to rescue Ross/Garcia?
    1. Force Vanessa to be a flier.
    2. Create a path in the mountains.
    3. Force any of Eirika up to Vanessa to be a flier.
    """

    display_name = "Rescue Ross method"
    option_Vanessa = 0
    option_Map = 1
    option_Early_Flier = 2
    default = 0

class EirikaClass(Choice):
    """
    Pick Eirika's class

    only works if Randomize Player Units is enabled
    """

    display_name = "Eirika class"
    option_Random_class = -1
    option_Combat_class = 0
    option_Ephraim_lord = 1
    option_Eirika_lord = 2
    option_Cavalier = 5
    option_Armour_Knight = 9
    option_Thief = 13
    option_Mercenary = 15
    option_Myrmidon = 19
    option_Archer = 25
    option_Fighter = 63
    option_Brigand = 65
    option_Pirate = 66
    option_Wyvern_Rider = 31
    option_Pegasus_Knight = 72
    option_Journeyman = 126
    option_Recruit = 55
    option_Pupil = 127
    option_Mage = 37
    option_Shaman = 45
    option_Monk = 68
    option_Troubadour=75
    option_Cleric = 74
    option_Priest = 69
    option_Manakete = 60
    option_Dancer = 77
    option_Bonewalker=84
    option_Bonewalker_Bow=85
    option_Bael = 88
    option_Mauthe_Doog = 91
    option_Tarvos = 93
    option_Mogall = 95
    option_Gargoyle= 99
    default = -1



class SmoothDeployments(Toggle):
    """
    Gate chapter progression on the size of your deployable army.
    Requires Enable recruit checks.

    Deploy permits become progression items and can be placed anywhere in the
    multiworld. Logic expects 8 deploy permits for early units (recruited by
    Chapter 7) before advancing past Chapter 8, and 11 deploy permits for
    early/mid units before advancing past Chapter 15.
    """

    display_name = "Smooth deployments"
    default = 1

class NoRandoThief(Toggle):
    """
    Don't randomize enemy theives

    So they can stop stealing your treasure
    """
    display_name = "Don't randomize enemy theives"
    default = 1

class StopBanditMounted(Toggle):
    """
    Stops enemys that destroy villages from being flying / mounted

    Needs "Enemy Randomization Results" to not be set to "no rando"
    """

    display_name = "No enhanced movement bandits"
    default = 0


class EnableTower(Toggle):
    """
    Make each floor of the Tower of Valni a check. This can help balance the
    amount of early/lategame checks a bit more.
    """

    display_name = "Enable Tower of Valni checks"
    default = 0


class EnableRuins(Toggle):
    """
    Make each floor of the Lagdou Ruins a check.
    """

    display_name = "Enable Lagdou Ruins checks"
    default = 0


class ShuffleSkirmishTables(Toggle):
    """
    Shuffle enemy spawn tables for the Tower, Ruins and skirmishes.
    """

    display_name = "Shuffle internal randomizer tables"
    default = 1


class LockpickUsability(Choice):
    """
    Allow units other than thieves to use lockpicks and the Rogue's Pick
    command.

    - Vanilla: Only Thieves, Assassins and Rogues can use lockpicks.
    - Global Lockpicks: All characters can use lockpicks.
    - Global Rogue pick: In addition to global lockpicks, all characters can use
      the Rogue class's "Pick" command.
    """

    display_name = "Lockpick usability"
    option_Vanilla = 0
    option_GlobalLockpicks = 1
    option_GlobalRoguePick = 2


class NormalizeGenders(Toggle):
    """
    Adjust female classes to have identical base stats and caps to their male
    counterparts, if one exists.

    In most cases, this is a buff to those classes. However, some low-turn
    strategies may rely on the fact that female mounted units have more Aid.
    """

    display_name = "Normalize gendered class stats"
    default = 0


class DeathLink(Choice):
    """
    When you die, everyone dies. Of course the reverse is true, too.
    """

    display_name = "DeathLink"
    option_off = 0
    alias_no = 0
    option_OnGameOver = 1
    alias_gameover = 1
    option_OnEveryDeath = 2
    alias_death = 2


class GrowthRando(Choice):
    """
    Randomizes growth rates.

    - Redistribute: Preserves growth total, possibly adjusted (positive or negative)
      between GrowthRandoMin and GrowthRandoMax.
    - Delta: Adjusts vanilla growths by amounts between GrowthRandoMin and GrowthRandoMax
    - Full Random: Growths are assigned randomly between GrowthRandoMin and GrowthRandoMax

    GrowthRandoMin and GrowthRandoMax control the min/max of the adjustment.
    """

    display_name = "Growth Randomizing"

    option_Vanilla = 0
    alias_no = 0
    alias_off = 0
    option_Redistribute = 1
    option_Delta = 2
    option_Full = 3


class GrowthRandoMin(Range):
    """
    See Growth Rando.
    """

    display_name = "Growth Rando Min"
    range_start = 0
    range_end = 255
    default = 10


class GrowthRandoMax(Range):
    """
    See Growth Rando.
    """

    display_name = "Growth Rando Max"
    range_start = 0
    range_end = 255
    default = 70


# CR-someday cam: think about how this interacts with creature campaign mode
class Goal(Choice):
    """
    Set the goal of the game.

    - Defeat Fomortiis: Defeat the usual final boss, which can take a long time.
    - Clear Valni: Clear the 8th floor of the Tower of Valni. Implies Enable Tower.
      Recommended for short- to medium-length games.
    - Defeat Tirado: Clear Chapter 8. Recommended for short games.
    - Clear Lagdou: Clear the 10th floor of the Lagdou Ruins. Implies Enable Ruins.

    Note that this option only change which check is considered the goal and
    does not affect progression logic at all.
    """

    display_name = "Goal"
    option_DefeatFormortiis = 0
    option_ClearValni = 1
    option_DefeatTirado = 2
    option_ClearLagdou = 3


class MusicRando(Choice):
    """
    Randomizes music tracks.

    - Context: Music tracks will be shuffled within the same group (battle themes
      will be randomized to other battle themes, etc)
    - Chaos: Music tracks will be shuffled randomly
    """
    display_name = "Random Music"
    option_Vanilla = 0
    alias_no = 0
    alias_off = 0
    option_Context = 1
    option_Chaos = 2
    alias_full = 2
    alias_all = 2


# CR-someday cam: Eventually, it would be nice to be able to generate this.
@dataclass
class FE8Options(PerGameCommonOptions):
    # Game Options
    death_link: DeathLink
    music_rando: MusicRando
    goal: Goal

    # Player Randomizer settings
    player_unit_rando: PlayerRando
    player_unit_monsters: PlayerMonsters
    eirika_class: EirikaClass
    random_myrrh: RandomMyrrh
    random_tethys: RandomTethys
    rescue_ross: RescueRoss
    force_healer: ForceHealer
    force_dancer: ForceDancer
    force_thief: ForceThief
    lockpick_usability: LockpickUsability
    easier_5x: Easier5x

    # Growth Rate Settings
    growth_rando: GrowthRando
    growth_rando_min: GrowthRandoMin
    growth_rando_max: GrowthRandoMax
    normalize_genders: NormalizeGenders

    # Enemy Randomizer Settings
    enemy_rando: EnemyRando
    super_demon_king: SuperDemonKing
    no_rando_thief: NoRandoThief
    stop_bandit_mounted: StopBanditMounted

    # Unitsanity
    recruit_checks_enabled: EnableRecruitChecks
    smooth_deployments: SmoothDeployments
    progressive_seth_deployment: ProgressiveSethDeployment
    first_healer_deployment: FirstHealerDeployment
    first_thief_deployment: FirstThiefDeployment

    # Level Caps / Settings
    enable_level_caps: EnableLevelCaps
    smooth_level_caps: SmoothLevelCapProgression
    min_endgame_level_cap: MinimumEndgameLevelCapRange

    # Weapon Caps / Settings
    enable_weapon_level_caps: EnableWeaponLevelCaps
    required_holy_weapons: MinimumUsableHolyWeapons
    exclude_latona: ExcludeLatona
    unbreakable_regalia: UnbreakableRegalia

    # Optional Fight Settings
    tower_enabled: EnableTower
    ruins_enabled: EnableRuins
    shuffle_skirmish_tables: ShuffleSkirmishTables
    # Convenience methods for options that imply each other

    def tower_checks_enabled(self):
        return bool(self.tower_enabled) or self.goal == Goal.option_ClearValni

    def ruins_checks_enabled(self):
        return bool(self.ruins_enabled) or self.goal == Goal.option_ClearLagdou

FE8_option_groups:dict[str, List[Any]] = {
    "Player Randomizer settings": [PlayerRando, PlayerMonsters, EirikaClass, RandomMyrrh, RandomTethys, ForceThief, 
                                   ForceHealer, ForceDancer, RescueRoss, Easier5x, LockpickUsability],

    "Growth Rate Settings": [GrowthRando, GrowthRandoMin, GrowthRandoMax, NormalizeGenders],

    "Enemy Randomizer Settings": [EnemyRando, SuperDemonKing, NoRandoThief, StopBanditMounted], 

    "Unitsanity": [EnableRecruitChecks, SmoothDeployments, ProgressiveSethDeployment, 
                   FirstHealerDeployment, FirstThiefDeployment],

    "Level Caps / Settings": [EnableLevelCaps, SmoothLevelCapProgression, MinimumEndgameLevelCapRange],

    "Weapon Caps / Settings": [EnableWeaponLevelCaps, MinimumUsableHolyWeapons, ExcludeLatona,
                                UnbreakableRegalia],

    "Optional Fight Settings": [ EnableTower, EnableRuins, ShuffleSkirmishTables]

} 
