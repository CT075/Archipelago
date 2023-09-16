from typing import Dict

from Options import Option, Range, Toggle


def round_up_to(x, mod):
    return ((x + mod - 1) // mod) * mod


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


fe8_options: Dict[str, type[Option]] = {
    "super_demon_king": SuperDemonKing,
    "smooth_level_caps": SmoothLevelCapProgression,
    "min_endgame_level_cap": MinimumEndgameLevelCapRange,
    "required_holy_weapons": MinimumUsableHolyWeapons,
    "exclude_latona": ExcludeLatona,
}
