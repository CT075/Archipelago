import asyncio
from typing import (
    TYPE_CHECKING,
    Optional,
    Dict,
    Set,
    Tuple,
    Any,
    Callable,
    TypeVar,
    Awaitable,
)
import json
import os
import subprocess
from functools import partial
from argparse import Namespace

import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient
from NetUtils import ClientStatus
from Utils import async_start
from settings import get_settings
import Patch

from .connector_config import locations, EXPECTED_ROM_NAME
from .constants import FE8_NAME, FE8_ID_PREFIX

if TYPE_CHECKING:
    from worlds._bizhawk.context import BizHawkClientContext
else:
    BizHawkClientContext = object

FOMORTIIS_FLAG = dict(locations)["Defeat Formortiis"]

T = TypeVar("T")


class FE8Client(BizHawkClient):
    game = FE8_NAME
    gba_push_pull_task: Optional[asyncio.Task]
    local_checked_locations: Set[int]
    game_state_safe: bool = False
    goal_flag: int = FOMORTIIS_FLAG

    def __init__(self, server_address: Optional[str], password: Optional[str]):
        super().__init__()
        self.local_checked_locations = set()

    async def validate_rom(self, ctx: BizHawkClientContext) -> bool:
        from CommonClient import logger

        try:
            rom_name_bytes = (await bizhawk.read(ctx.bizhawk_ctx, [(0xA0, 16, "ROM")]))[
                0
            ]
            rom_name = bytes([byte for byte in rom_name_bytes if byte != 0]).decode(
                "ascii"
            )
            if not rom_name.startswith("FIREEMBLEM2E"):
                return False
            if rom_name == "FIREEMBLEM2EBE8E":
                logger.info(
                    "ERROR: You seem to be running an unpatched version of FE8. "
                    "Please generate a patch file and use it to create a patched ROM."
                )
                return False
            if rom_name != EXPECTED_ROM_NAME:
                logger.info(
                    "ERROR: The patch file used to create this ROM is not compatible "
                    "with this client. Double check your client version against the "
                    "version used by the generator."
                )
                return False
        except UnicodeDecodeError:
            return False
        except bizhawk.RequestFailedError:
            return False

        ctx.game = self.game
        ctx.items_handling = 1
        ctx.want_slot_data = True
        ctx.watcher_timeout = 0.125

        return True

    async def run_locked(
        self,
        ctx: BizHawkClientContext,
        f: Callable[[BizHawkClientContext], Awaitable[T]],
    ) -> T:
        await bizhawk.lock(ctx.bizhawk_ctx)
        result = await f(ctx)
        await bizhawk.unlock(ctx.bizhawk_ctx)
        return result

    async def update_game_state(self, ctx: BizHawkClientContext) -> None:
        from .constants import (
            PROC_SIZE,
            PROC_POOL_EWRAM_OFFS,
            TOTAL_NUM_PROCS,
            WM_PROC_ADDRESS,
            E_PLAYERPHASE_PROC_ADDRESS,
        )

        active_procs = [
            int.from_bytes(i, byteorder="little")
            for i in await bizhawk.read(
                ctx.bizhawk_ctx,
                [
                    (PROC_POOL_EWRAM_OFFS + i * PROC_SIZE, 4, "EWRAM")
                    for i in range(TOTAL_NUM_PROCS)
                ],
            )
        ]

        if any(
            proc in (WM_PROC_ADDRESS, E_PLAYERPHASE_PROC_ADDRESS)
            for proc in active_procs
        ):
            self.game_state_safe = True
        else:
            self.game_state_safe = False

    async def set_auth(self, ctx: BizHawkClientContext) -> None:
        from .connector_config import SLOT_NAME_ADDR

        slot_name_bytes = (
            await bizhawk.read(ctx.bizhawk_ctx, [(SLOT_NAME_ADDR, 64, "ROM")])
        )[0]
        ctx.auth = bytes([byte for byte in slot_name_bytes if byte != 0]).decode(
            "utf-8"
        )

    # requires: locked and game_state_safe
    async def maybe_write_next_item(self, ctx: BizHawkClientContext) -> None:
        from .connector_config import (
            ARCHIPELAGO_RECEIVED_ITEM_ADDR,
            ARCHIPELAGO_NUM_RECEIVED_ITEMS_ADDR,
        )

        is_filled, num_items_received_bytes = await bizhawk.read(
            ctx.bizhawk_ctx,
            [
                (ARCHIPELAGO_RECEIVED_ITEM_ADDR + 2, 1, "EWRAM"),
                (ARCHIPELAGO_NUM_RECEIVED_ITEMS_ADDR, 4, "EWRAM"),
            ],
        )

        if is_filled:
            return

        num_items_received = int.from_bytes(
            num_items_received_bytes, byteorder="little"
        )

        if num_items_received < len(ctx.items_received):
            next_item = ctx.items_received[num_items_received]
            await bizhawk.write(
                ctx.bizhawk_ctx,
                [
                    (
                        ARCHIPELAGO_RECEIVED_ITEM_ADDR + 0,
                        (next_item.item - FE8_ID_PREFIX).to_bytes(2, "little"),
                        "EWRAM",
                    ),
                    (
                        ARCHIPELAGO_RECEIVED_ITEM_ADDR + 2,
                        b"\x01",
                        "EWRAM",
                    ),
                    (
                        ARCHIPELAGO_NUM_RECEIVED_ITEMS_ADDR,
                        num_items_received.to_bytes(4, "little"),
                        "EWRAM",
                    ),
                ],
            )

    async def game_watcher(self, ctx: BizHawkClientContext) -> None:
        from .connector_config import FLAGS_OFFSET

        try:
            await self.update_game_state(ctx)

            if self.game_state_safe:
                await self.run_locked(ctx, self.maybe_write_next_item)

            flag_bytes = (await bizhawk.read(ctx.bizhawk_ctx, [(FLAGS_OFFSET, 8, "EWRAM")]))[0]
            local_checked_locations = set()

            for byte_i, byte in enumerate(flag_bytes):
                for i in range(8):
                    if byte & (1 << i) != 0:
                        flag_id = byte_i * 8 + i
                        location_id = flag_id + FE8_ID_PREFIX

                        if location_id in ctx.server_locations:
                            local_checked_locations.add(location_id)

                        if flag_id == self.goal_flag:
                            game_clear = True

            if local_checked_locations != self.local_checked_locations:
                self.local_checked_locations = local_checked_locations

                if local_checked_locations is not None:
                    await ctx.send_msgs(
                        [
                            {
                                "cmd": "LocationChecks",
                                "locations": list(local_checked_locations),
                            }
                        ]
                    )

            if not ctx.finished_game and game_clear:
                await ctx.send_msgs(
                    [{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]
                )
        except bizhawk.RequestFailedError:
            pass
