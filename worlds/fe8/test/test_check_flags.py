import unittest

from ..client import decode_flag_ids
from ..connector_config import locations, FLAGS_SIZE


class TestCheckFlagRange(unittest.TestCase):
    def test_all_location_flags_fit_in_flag_buffer(self) -> None:
        # Regression guard: the client reads FLAGS_SIZE bytes of check flags,
        # so every location's flag index must fit in that window. An earlier
        # version hardcoded an 8-byte read, silently dropping every recruit
        # check with flag id >= 64 (Joshua through Syrene).
        max_flag = max(flag_id for _, flag_id in locations)
        self.assertLess(max_flag, FLAGS_SIZE * 8)

    def test_decode_sees_flags_beyond_byte_eight(self) -> None:
        joshua = dict(locations)["Joshua Recruited"]
        self.assertGreaterEqual(joshua, 64)

        flag_bytes = bytearray(FLAGS_SIZE)
        flag_bytes[joshua // 8] |= 1 << (joshua % 8)
        self.assertEqual(decode_flag_ids(bytes(flag_bytes)), {joshua})

    def test_decode_empty(self) -> None:
        self.assertEqual(decode_flag_ids(bytes(FLAGS_SIZE)), set())
