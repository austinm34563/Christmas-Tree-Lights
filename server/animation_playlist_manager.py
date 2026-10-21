
from json import load, dump
from pathlib import Path
from enum import Enum
from logger import Logger
from animation_playlist import AnimationPlaylistData
from dataclasses import asdict

ANIMATION_PLAYLISTS_FILE = "data/playlists.json"
TAG = "AnimationPlaylistManager"


class AnimationPlaylistManager:
    def __init__(self):
        self.__read()

    def get_playlists(self):
        return self.playlists

    def add(self, playlist_name, playlist):
        self.playlists[playlist_name] = asdict(playlist)
        self.__write()

    def remove(self, playlist_name):
        self.playlists.pop(playlist_name)
        self.__write()

    def __read(self):
        file_path = Path(ANIMATION_PLAYLISTS_FILE)
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            with open(file_path, "w", encoding="utf-8") as file:
                dump({}, file, indent=4)
            self.playlists = {}
            return

        with open(file_path, 'r', encoding='utf-8') as file:
            self.playlists = load(file)

    def __write(self):
        file_path = Path(ANIMATION_PLAYLISTS_FILE)
        with open(file_path, "w", encoding="utf-8") as file:
            dump(self.playlists, file, indent=4)

if __name__ == "__main__":
    from time import sleep
    apm = AnimationPlaylistManager()
    animations = ["Cycle Fade", "Fade"]
    palettes = ["Halloween Spooky", "Halloween Pumpkin"]
    speeds = [1,2]
    apm.add("new playlist", AnimationPlaylistData(animations, palettes, speeds))
    sleep(2)
    apm.add("new playlist 2", AnimationPlaylistData(animations, palettes, speeds))
    sleep(2)
    apm.remove("new playlist")
