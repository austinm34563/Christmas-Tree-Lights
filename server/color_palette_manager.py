
from json import load, dump
from pathlib import Path
from enum import Enum
from color_palettes import DEFAULT_COLOR_PALETTES
from logger import Logger

COLOR_PALETTES_FILE = "data/palettes.json"
TAG = "ColorPaletteManager"

class ColorPaletteReturnStatus(Enum):
    OK = 0
    MODIFIED_DEFAULT_ERR = 1


class ColorPaletteManager:
    def __init__(self):
        self.palettes = {}
        self.__read()

    def get_color_palettes(self):
        return self.palettes

    def add(self, palette_name, colors):
        if palette_name in DEFAULT_COLOR_PALETTES:
            Logger.error(TAG, "Cannot modify a default palette")
            return ColorPaletteReturnStatus.MODIFIED_DEFAULT_ERR
        self.palettes[palette_name] = colors
        self.__write()
        return ColorPaletteReturnStatus.OK

    def remove(self, palette_name):
        if palette_name in DEFAULT_COLOR_PALETTES:
            Logger.error(TAG, "Cannot modify a default palette")
            return ColorPaletteReturnStatus.MODIFIED_DEFAULT_ERR
        self.palettes.pop(palette_name)
        self.__write()
        return ColorPaletteReturnStatus.OK

    def __read(self):
        file_path = Path(COLOR_PALETTES_FILE)
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            with open(file_path, "w", encoding="utf-8") as file:
                dump(DEFAULT_COLOR_PALETTES, file, indent=4)
            self.palettes = DEFAULT_COLOR_PALETTES
            return

        with open(file_path, 'r', encoding='utf-8') as file:
            self.palettes = load(file)

    def __write(self):
        file_path = Path(COLOR_PALETTES_FILE)
        with open(file_path, "w", encoding="utf-8") as file:
            dump(self.palettes, file, indent=4)
