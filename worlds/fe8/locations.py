from typing import Optional

from BaseClasses import Location, LocationProgressType

from .constants import FE8_NAME, FE8_ID_PREFIX


class FE8Location(Location):
    game = FE8_NAME
    #progress_type = LocationProgressType.PRIORITY

    def __init__(self, player: int, name, code: int, parent):
        super(FE8Location, self).__init__(player, name, FE8_ID_PREFIX + code, parent)
        self.event = None

    def local_id(self) -> Optional[int]:
        if self.code is not None:
            return self.code - FE8_ID_PREFIX
        else:
            return None
