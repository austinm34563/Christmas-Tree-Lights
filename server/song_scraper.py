
import eyed3
from os import listdir
from os.path import isfile, join

SONG_DIRECTORY = "./songs"

def get_songs():
    return [file for file in listdir(SONG_DIRECTORY) if isfile(join(SONG_DIRECTORY, file)) and file.endswith('.mp3')]


def get_mp3_metadata():
    song_files = get_songs()
    metadata_dict = {}

    for song in song_files:
        audio_file = eyed3.load(join(SONG_DIRECTORY, song))

        # we only care about songs with metadata
        if audio_file.tag.title is None or audio_file.tag.artist is None or audio_file.tag.album is None:
            continue

        metadata_dict[song] = {
            "title": audio_file.tag.title,
            "artist": audio_file.tag.artist,
            "album": audio_file.tag.album,
        }

    return metadata_dict
