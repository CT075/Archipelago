from worlds.Files import APDeltaPatch

from .constants import FE8_NAME

'''
class FE8DeltaPatch(APDeltaPatch):
    game = FE8_NAME
    hash = "005531fef9efbb642095fb8f64645236"
    patch_file = ".apfe8"
    result_file_ending = ".gba"

    @classmethod
    def get_source_data(cls) -> bytes:
        return get_base_rom_as_bytes()

def get_base_rom_as_bytes() -> bytes:
    with open(get_settings().fe8_settings.rom_file, "rb") as infile:
        base_rom_bytes = bytes(infile.read())

    return base_rom_bytes
'''
