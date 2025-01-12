import os
from pytubefix import YouTube
from pydub import AudioSegment
from mutagen.easyid3 import EasyID3
from logger import Logger


SONG_DIRECTORY = "./songs"
TAG = "SongDownloadManager"

def download_music(url, title, artist):

    yt = YouTube(url)
    yt_audio_stream = yt.streams.get_audio_only()

    # get audio name/path
    audio_file_name = title + "_" + artist + ".m4a"
    audio_file_name = audio_file_name.replace(" ", "_")
    audio_path = os.path.join(SONG_DIRECTORY, audio_file_name)
    Logger.info(TAG, f"Downloading {url} into {audio_path}")

    # download the stream
    yt_audio_stream.download(output_path=SONG_DIRECTORY, filename=audio_file_name)

    # convert to mp3
    convert_to_mp3(audio_path, title, artist)

def convert_to_mp3(file_path, title, artist):
    # Ensure the input file has a .m4a extension
    if not file_path.lower().endswith(".m4a"):
        raise ValueError("Input file must have a .m4a extension")

    # Define the output file path with .mp3 extension
    mp3_path = file_path[:-4] + ".mp3"

    # Convert the m4a file to mp3
    audio = AudioSegment.from_file(file_path, format="m4a")
    audio.export(mp3_path, format="mp3")
    Logger.info(TAG, f"Converted {file_path} to {mp3_path}")

    # Add metadata to the MP3 file
    add_metadata(mp3_path, title, artist)

    # Remove the original .m4a file
    os.remove(file_path)
    Logger.info(TAG, f"Removed original file: {file_path}")

    return mp3_path

def add_metadata(mp3_path, title, artist):
    try:
        audio_file = EasyID3(mp3_path)
    except mutagen.id3.ID3NoHeaderError:
        audio_file = EasyID3()

    # Set title and artist metadata
    audio_file["title"] = title
    audio_file["artist"] = artist
    audio_file.save()
    Logger.info(TAG, f"Added metadata: Title='{title}', Artist='{artist}' to {mp3_path}")


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=H5HzOqmE9Mk"
    download_music(url, "No Way OUt", "Squid Game")