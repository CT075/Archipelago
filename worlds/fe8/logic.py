from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

JsonValue = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]

_KNOWN_BOOL_FIELDS = {"must_fight", "must_fly", "no_store", "player", "monster", "ignore"}


@dataclass
class Nudges:
    start: Optional[tuple[int, int]] = None
    by_index: dict[int, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def of_object(cls, obj: dict[str, JsonValue]) -> "Nudges":
        start = None
        by_index: dict[int, tuple[int, int]] = {}
        for k, v in obj.items():
            x, y = v
            if k == "start":
                start = (x, y)
            else:
                by_index[int(k)] = (x, y)
        return cls(start=start, by_index=by_index)


@dataclass
class AI1Mod:
    from_id: int
    to_id: int

    @classmethod
    def of_object(cls, obj: dict[str, JsonValue]) -> "AI1Mod":
        return cls(from_id=obj["from"], to_id=obj["to"])


@dataclass
class Logic:
    tags: set[str] = field(default_factory=set)
    must_fight: bool = False
    must_fly: bool = False
    no_store: bool = False
    player: bool = False
    monster: bool = False
    ignore: bool = False
    nudges: Optional[Nudges] = None
    ai1_mod: Optional[AI1Mod] = None

    # Keys that have been explicitly assigned, whether or not the assigned
    # value was truthy. Lets `set_default` avoid clobbering an explicit
    # `False`/`{}` with the default it would otherwise apply.
    _explicit: set[str] = field(default_factory=set, repr=False)

    @classmethod
    def of_object(cls, obj: dict[str, JsonValue]) -> "Logic":
        logic = cls()
        for k, v in obj.items():
            logic.set(k, v)
        return logic

    def set(self, key: str, value: JsonValue) -> None:
        self._explicit.add(key)
        if key == "nudges":
            self.nudges = Nudges.of_object(value)
        elif key == "ai1_mod":
            self.ai1_mod = AI1Mod.of_object(value)
        elif key == "comment":
            return
        elif key in _KNOWN_BOOL_FIELDS:
            setattr(self, key, bool(value))
        elif value:
            self.tags.add(key)

    def set_default(self, key: str) -> None:
        """Set `key` to a truthy default, unless it's already been explicitly
        assigned (e.g. by a per-unit override in the source JSON)."""
        if key not in self:
            self.set(key, True)

    def __contains__(self, key: str) -> bool:
        return key in self._explicit or key in self.tags

    def no_tags(self) -> set[str]:
        """Job tags forbidden by this unit's `no_<tag>` flags."""
        return {t.removeprefix("no_") for t in self.tags if t.startswith("no_")}
