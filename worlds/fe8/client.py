import asyncio
from typing import Optional, Dict, Set, Tuple, Any
import json
import os
import subprocess
from argparse import Namespace

from CommonClient import (
    CommonContext,
    ClientCommandProcessor,
    get_base_parser,
    server_loop,
    gui_enabled,
    logger,
)
from NetUtils import ClientStatus
from Utils import async_start
from settings import get_settings
import Patch

from .data import locations
from .constants import FE8_NAME, FE8_ID_PREFIX

GBA_SOCKET_PORT = 43053

EXPECTED_SCRIPT_VERSION = 1

CONNECTION_STATUS_TIMING_OUT = (
    "Connection timing out. Please restart your emulator and connector_fe8.lua."
)
CONNECTION_STATUS_REFUSED = (
    "Connection refused. Please start your emulator and connector_fe8.lua."
)
CONNECTION_STATUS_RESET = (
    "Connection reset. Please restart your emulator and connector_fe8.lua."
)
CONNECTION_STATUS_TENTATIVE = "Initial connection made"
CONNECTION_STATUS_CONNECTED = "Connected"
CONNECTION_STATUS_INITIAL = "Connection has not been initiated"

FOMORTIIS_FLAG = dict(locations)["Defeat Formortiis"]


class GBACommandProcessor(ClientCommandProcessor):
    def _cmd_gba(self) -> None:
        """Check GBA Connection State"""
        if isinstance(self.ctx, GBAContext):
            logger.info(f"GBA Status: {self.ctx.gba_status}")


class GBAContext(CommonContext):
    game = FE8_NAME
    command_processor = GBACommandProcessor
    items_handling = 1
    gba_streams: Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    gba_status: Optional[str]
    awaiting_rom = False
    gba_push_pull_task: Optional[asyncio.Task]
    local_checked_locations: Set[int]
    goal_flag: int = FOMORTIIS_FLAG

    def __init__(self, server_address: Optional[str], password: Optional[str]):
        super().__init__(server_address, password)
        self.gba_streams = None
        self.gba_status = CONNECTION_STATUS_INITIAL
        self.gba_push_pull_task = None
        self.local_checked_locations = set()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(GBAContext, self).server_auth(password_requested)
        if self.auth is None:
            self.awaiting_rom = True
            logger.info("Awaiting connection to GBA to get Player info")
            return
        await self.send_connect()

    def run_gui(self):
        from kvui import GameManager

        class GBAManager(GameManager):
            base_title = "Archipelago FE8 Client"

        self.ui = GBAManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


def create_payload(ctx: GBAContext) -> str:
    payload = json.dumps(
        {
            "items": [
                [item.item - FE8_ID_PREFIX, item.flags & 1]
                for item in ctx.items_received
            ]
        }
    )

    return payload


async def handle_read_data(gba_data: Dict[str, Any], ctx: GBAContext):
    local_checked_locations = set()
    game_clear = False

    if "slot_name" in gba_data:
        if ctx.auth is None:
            ctx.auth = bytes(
                [byte for byte in gba_data["slot_name"] if byte != 0]
            ).decode("utf-8")
            if ctx.awaiting_rom:
                await ctx.server_auth(False)

    if "flag_bytes" in gba_data:
        for byte_i, byte in enumerate(gba_data["flag_bytes"]):
            for i in range(8):
                if byte & (1 << i) != 0:
                    flag_id = byte_i * 8 + i
                    location_id = flag_id + FE8_ID_PREFIX

                    if location_id in ctx.server_locations:
                        local_checked_locations.add(location_id)

                    if flag_id == ctx.goal_flag:
                        game_clear = True

        if local_checked_locations != ctx.local_checked_locations:
            ctx.local_checked_locations = local_checked_locations

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


async def gba_send_receive_task(ctx: GBAContext):
    logger.info("Waiting to connect to GBA. Use /gba for status information.")
    while not ctx.exit_event.is_set():
        error_status: Optional[str] = None

        if ctx.gba_streams is None:
            try:
                logger.debug("Attempting to connect to GBA...")
                ctx.gba_streams = await asyncio.wait_for(
                    asyncio.open_connection("localhost", GBA_SOCKET_PORT), timeout=10
                )
                ctx.gba_status = CONNECTION_STATUS_TENTATIVE
            except asyncio.TimeoutError:
                logger.debug("Connection to GBA timed out. Retrying...")
                ctx.gba_status = CONNECTION_STATUS_TIMING_OUT
                continue
            except ConnectionRefusedError:
                logger.debug("Connection to GBA refused. Retrying.")
                ctx.gba_status = CONNECTION_STATUS_REFUSED
                continue
        else:
            reader, writer = ctx.gba_streams

            message = create_payload(ctx).encode("utf-8")
            writer.write(message)
            writer.write(b"\n")

            try:
                await asyncio.wait_for(writer.drain(), timeout=2)
            except asyncio.TimeoutError:
                logger.debug("Connection to GBA timed out. Reconnecting...")
                error_status = CONNECTION_STATUS_TIMING_OUT
                writer.close()
                ctx.gba_streams = None
            except ConnectionResetError:
                logger.debug("Connection to GBA lost. Reconnecting...")
                error_status = CONNECTION_STATUS_RESET
                writer.close()
                ctx.gba_streams = None

            try:
                data_bytes = await asyncio.wait_for(reader.readline(), timeout=5)
                data_decoded = json.loads(data_bytes.decode("utf-8"))

                if data_decoded["script_version"] != EXPECTED_SCRIPT_VERSION:
                    logger.warning(
                        f"Your connector script is incompatible with this client. Expected version {EXPECTED_SCRIPT_VERSION}, got {data_decoded['script_version']}."
                    )
                    break

                async_start(handle_read_data(data_decoded, ctx))
            except asyncio.TimeoutError:
                logger.debug("Connection to GBA timed out during read. Reconnecting.")
                error_status = CONNECTION_STATUS_TIMING_OUT
                writer.close()
                ctx.gba_streams = None
            except ConnectionResetError:
                logger.debug("Connection to GBA lost during read. Reconnecting.")
                error_status = CONNECTION_STATUS_RESET
                writer.close()
                ctx.gba_streams = None

            if error_status:
                ctx.gba_status = error_status
                logger.info(
                    "Lost connection to GBA and attempting to reconnect. Use /gba for status updates"
                )
            elif ctx.gba_status == CONNECTION_STATUS_TENTATIVE:
                logger.info("Connected to GBA")
                ctx.gba_status = CONNECTION_STATUS_CONNECTED


async def run_game(rom_file_path: str) -> None:
    auto_start = get_settings()["fe8_settings"].get("rom_start", True)
    if auto_start is True:
        import webbrowser

        webbrowser.open(rom_file_path)
    elif os.path.isfile(auto_start):
        subprocess.Popen(
            [auto_start, rom_file_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


async def patch_and_run_game(patch_file_path: str) -> None:
    meta_data, output_file_path = Patch.create_rom_file(patch_file_path)
    async_start(run_game(output_file_path))


parser = get_base_parser()
parser.add_argument(
    "apfe8_file", default="", type=str, nargs="?", help="Path to an APFE8 file"
)
args = parser.parse_args()


def launch() -> None:
    async def main(args: Namespace) -> None:
        ctx = GBAContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")

        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        if args.apfe8_file:
            logger.info("Beginning patching process...")
            async_start(patch_and_run_game(args.apfe8_file))

        ctx.gba_push_pull_task = asyncio.create_task(
            gba_send_receive_task(ctx), name="GBA Push/Pull"
        )

        await ctx.exit_event.wait()
        await ctx.shutdown()

    import colorama

    colorama.init()
    asyncio.run(main(args))
    colorama.deinit()
