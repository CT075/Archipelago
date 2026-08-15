from dataclasses import dataclass

from Options import Choice, Range, Toggle, PerGameCommonOptions

from .constants import (
    ALL_RECRUITS,
    EARLY_UNITS,
    MID_UNITS,
)


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


class UnbreakableRegalia(Toggle):
    """
    Make all holy weapons other than Latona unbreakable.
    """

    display_name = "Unbreakable Regalia"
    default = 0


class EnableRecruitChecks(Toggle):
    """
    Make each character recruitment a check. Adds up to 31 locations (one per
    recruitable unit) and adds deploy permit items to the item pool, so
    units must be unlocked before they can be deployed on the prep screen.

    Goals that end before the last chapter leave out the units they can't
    reach; those units are freely deployable instead.
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


class EnablePromotionUnlocks(Toggle):
    """
    Gate class promotion behind Archipelago items. Adds one "... Promotion"
    item per promoted class (Great Lord is always available); units cannot
    promote into a class until its item has been received. Also makes the
    super trainee path available from the start of the game.

    When disabled, promotion behaves as in the vanilla game.
    """

    display_name = "Enable promotion unlocks"
    default = 0


class SmoothDeployments(Toggle):
    """
    Gate chapter progression on the size of your deployable army.
    Requires Enable recruit checks.

    Deploy permits become progression items and can be placed anywhere in the
    multiworld. Logic expects 8 deploy permits for early units (recruited by
    Chapter 8) before advancing past Chapter 8, and 11 deploy permits for
    early/mid units before advancing past Chapter 16.
    """

    display_name = "Smooth deployments"
    default = 1


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
    Set the goal of the game, listed here shortest first.

    - Defeat Tirado: Clear Chapter 8. Recommended for short games.
    - Defeat Orson: Clear Chapter 16, the first chapter after the routes merge.
      Recommended for short- to medium-length games.
    - Clear Valni: Clear the 8th floor of the Tower of Valni. Implies Enable Tower.
      Recommended for medium-length games.
    - Defeat Fomortiis: Defeat the usual final boss, which can take a long time.
    - Clear Lagdou: Clear the 10th floor of the Lagdou Ruins. Implies Enable Ruins.
      The Ruins only exist in the Creature Campaign, so this goal requires
      defeating Formortiis first, making it the longest goal of all.

    This option does not otherwise affect progression logic, but goals that end
    early leave out the recruit checks and deploy permits for units you would
    never meet.
    """

    display_name = "Goal"
    option_DefeatFormortiis = 0
    option_ClearValni = 1
    option_DefeatTirado = 2
    option_ClearLagdou = 3
    option_DefeatOrson = 4


# The check that counts as victory for each goal. Used by both the generator
# (completion_condition) and the client (goal flag).
GOAL_LOCATIONS: dict[int, str] = {
    Goal.option_DefeatTirado: "Complete Chapter 8",
    Goal.option_DefeatOrson: "Complete Chapter 16",
    Goal.option_ClearValni: "Complete Tower of Valni 8",
    Goal.option_DefeatFormortiis: "Defeat Formortiis",
    Goal.option_ClearLagdou: "Complete Lagdou Ruins 10",
}

# Units each goal is able to recruit before it ends the run. Lagdou Ruins only
# exist in the Creature Campaign, which unlocks once Formortiis is dead, so that
# goal sits past the end of the story and reaches everyone.
GOAL_RECRUITS: dict[int, frozenset[str]] = {
    Goal.option_DefeatTirado: EARLY_UNITS,
    Goal.option_DefeatOrson: EARLY_UNITS | MID_UNITS,
    Goal.option_ClearValni: EARLY_UNITS | MID_UNITS,
    Goal.option_DefeatFormortiis: ALL_RECRUITS,
    Goal.option_ClearLagdou: ALL_RECRUITS,
}


class MusicRando(Choice):
    """
    Randomizes music tracks.

    - Context: Music tracks will be shuffled within the same group (battle themes
      will be randomized to other battle themes, etc)
    - Chaos: Music tracks will be shuffled randomly
    """

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
    player_unit_rando: PlayerRando
    player_unit_monsters: PlayerMonsters
    super_demon_king: SuperDemonKing
    smooth_level_caps: SmoothLevelCapProgression
    enable_level_caps: EnableLevelCaps
    enable_weapon_level_caps: EnableWeaponLevelCaps
    min_endgame_level_cap: MinimumEndgameLevelCapRange
    required_holy_weapons: MinimumUsableHolyWeapons
    exclude_latona: ExcludeLatona
    easier_5x: Easier5x
    unbreakable_regalia: UnbreakableRegalia
    recruit_checks_enabled: EnableRecruitChecks
    progressive_seth_deployment: ProgressiveSethDeployment
    smooth_deployments: SmoothDeployments
    promotion_unlocks: EnablePromotionUnlocks
    tower_enabled: EnableTower
    ruins_enabled: EnableRuins
    shuffle_skirmish_tables: ShuffleSkirmishTables
    lockpick_usability: LockpickUsability
    normalize_genders: NormalizeGenders
    death_link: DeathLink
    growth_rando: GrowthRando
    growth_rando_min: GrowthRandoMin
    growth_rando_max: GrowthRandoMax
    music_rando: MusicRando
    goal: Goal

    # Convenience methods for options that imply each other

    def tower_checks_enabled(self):
        return bool(self.tower_enabled) or self.goal == Goal.option_ClearValni

    def ruins_checks_enabled(self):
        return bool(self.ruins_enabled) or self.goal == Goal.option_ClearLagdou

    def available_recruits(self) -> frozenset[str]:
        """Units recruitable before the goal ends the run."""
        return GOAL_RECRUITS[self.goal.value]

    def excluded_recruits(self) -> frozenset[str]:
        """Units the goal can never reach, so they get no check and no permit.

        With recruit checks off there are no permits at all and the ROM lets
        everyone deploy, so nothing needs excluding.
        """
        if not self.recruit_checks_enabled:
            return frozenset()
        return ALL_RECRUITS - self.available_recruits()
