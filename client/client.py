import socket
import json
from time import sleep

HOST = 'raspberrypi.local'  # Replace with the Raspberry Pi's IP address on the Wi-Fi network
PORT = 65432          # The port used by the server

CHRISTMAS_PALETTES = {}
ANIMATION_OPTIONS = {}
SONG_OPTIONS = {}


def pick_command():
    """
    Helper method to prompt the user to pick a command.

    :return: Associated command id
    """
    print("Here are the list of commands:")
    print("1. Set Light")
    print("2. Pick Effect")
    print("3. Pick Pallette")
    print("4. Start Music Sync")
    print("5. Stop Music Sync")
    print("6. Create and start animation playlist")
    print("7. Stop animation playlist")
    print("8. Download song from YouTube URL")
    print("9. Refresh song list")
    return input("Enter command to send to server (or 'exit' to quit): ")


def convert_integer_input(integer: str):
    """
    Helper method to allow users to enter hex or dec for colors. Ideally
    users will enter colors in 0xRRGGBB format, but the option is there if
    they want to ented the value in dec.

    :param integer: integer string value
    :return: converted string into int
    """
    # Check if the input starts with '0x' or '0X' to identify hex
    return int(integer, 16) \
           if integer.startswith("0x") or integer.startswith("0X") \
           else int(integer)


def send_set_light_command():
    """
    Prompts user to enter color info. This color info is then sent to the
    rasberry pi server via JSON-RPC.

    :return: associated JSON-RPC request string
    """
    color = convert_integer_input(input("Enter a color: "))
    json_data = {
        "method" : "set_light",
        "params" : {
            "color" : str(hex(color))
        }
    }
    return json.dumps(json_data), False



def send_trigger_effect_command():
    """
    Prompts user for trigger info. Once info is received,
    info is converted to JSON and sent to rasberry pi.

    :return: associated JSON-RPC request string
    """
    # present animation IDs
    print()
    names = list(ANIMATION_OPTIONS.keys())
    for index, effect in enumerate(names):
        info = ANIMATION_OPTIONS[effect]
        description = info["description"]
        print(f"{index + 1}. {effect}:\n  - {description}")
    effect_index = int(input("Enter an animation id from above: "))
    effect = ANIMATION_OPTIONS[names[effect_index - 1]]["id"]

    # specify color scheme/palette options
    print("\nPick the following Color Scheme:")
    names = list(CHRISTMAS_PALETTES.keys())
    for index, pallete in enumerate(names):
        print(f"{index + 1}. {pallete}")

    # specifies an option for pre-loaded color on pi server
    print(f"{len(names) + 1}. Default colors loaded on pi server.")

    scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
    scheme = CHRISTMAS_PALETTES[names[scheme_choice - 1]] if scheme_choice <= len(names) else []

    # present speed options
    print("Enter a desired speed.\n - 1.0 = default\n - 2.0 = double speed\n - 0.5 = half speed")
    speed = float(input("Enter speed: "))

    # fill json data
    json_data = {
        "method" : "trigger_effect",
        "params" : {
            "animation_id" : effect,
            "color_scheme" : scheme,
            "speed" : speed
        }
    }
    return json.dumps(json_data), False


def send_set_pallete_command():
    """
    Prompts user for color pallete info. Once info is received, the JSON
    data is created and returned.

    @return associated JSON-RPC request string
    """
    print("Pick the following Pallete:")
    names = list(CHRISTMAS_PALETTES.keys())
    for index, pallete in enumerate(names):
        print(f"{index + 1}. {pallete}")
    pallete_choice = int(input("Choose a pallete from the list above: "))
    if pallete_choice > len(names) or pallete_choice <= 0:
        print("Invalid coice, defaulting to 1")
        pallete_choice = 1
    json_data = {
        "method" : "set_pallete",
        "params" : {
            "pallete" : CHRISTMAS_PALETTES[names[pallete_choice - 1]]
        }
    }
    return json.dumps(json_data), False


def send_start_music_sync_command():
    """
    Prompts user for music sync info.

    :return: associated JSON-RPC request string
    """
    # present animation IDs
    print()
    for index, id in enumerate(SONG_OPTIONS.keys()):
        title = SONG_OPTIONS[id]["title"]
        artist = SONG_OPTIONS[id]["artist"]
        print(f"{index + 1}. {title} by {artist}")
    song_ids = list(SONG_OPTIONS.keys())
    choice = int(input("Choose a song from list above: "))
    song = int(song_ids[choice - 1])

    # specify color scheme/palette options
    print("\nPick the following Color Scheme:")
    names = list(CHRISTMAS_PALETTES.keys())
    for index, pallete in enumerate(names):
        print(f"{index + 1}. {pallete}")

    # specifies an option for pre-loaded color on pi server
    print(f"{len(CHRISTMAS_PALETTES.keys()) + 1}. Default colors loaded on pi server.")

    scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
    scheme = CHRISTMAS_PALETTES[names[scheme_choice - 1]] if scheme_choice <= len(names) else []

    # fill json data
    json_data = {
        "method" : "play_song",
        "params" : {
            "song_id" : song,
            "pallete" : scheme,
        }
    }
    return json.dumps(json_data), False

def send_stop_music_sync_command():
    """Constructs `stop_songs` command"""

    # fill json data
    json_data = {
        "method" : "stop_song",
        "params" : {}
    }
    return json.dumps(json_data), False

def send_start_animation_playlist_command():
    """Prompts a user to generate and send a playlist of animations"""
    add_animation = True
    animations = []
    while add_animation:
        print()
        names = list(ANIMATION_OPTIONS.keys())
        for index, effect in enumerate(names):
            info = ANIMATION_OPTIONS[effect]
            description = info["description"]
            print(f"{index + 1}. {effect}:\n  - {description}")
        effect_index = int(input("Enter an animation id from above: "))
        effect = ANIMATION_OPTIONS[names[effect_index - 1]]["id"]

        # present speed options
        print("Enter a desired speed.\n - 1.0 = default\n - 2.0 = double speed\n - 0.5 = half speed")
        speed = float(input("Enter speed: "))

        animations.append(
            {
                "animation_id": effect,
                "speed": speed
            }
        )

        add_animation = input("\nWould you like to add another animation to the playlist? (Y/n): ").strip().upper() == "Y"

    add_color_scheme = True
    color_schemes = []
    while add_color_scheme:
        # specify color scheme/palette options
        print("\nPick the following Color Scheme:")
        names = list(CHRISTMAS_PALETTES.keys())
        for index, pallete in enumerate(names):
            print(f"{index + 1}. {pallete}")

        # specifies an option for pre-loaded color on pi server
        print(f"{len(names) + 1}. Default colors loaded on pi server.")

        scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
        scheme = CHRISTMAS_PALETTES[names[scheme_choice - 1]] if scheme_choice <= len(names) else []
        color_schemes.append(scheme)

        add_color_scheme = input("\nWould you like to add another color scheme? (Y/n): ").strip().upper() == "Y"

    time_delay = int(input("\nEnter the time delay between each animation (in seconds): "))

    json_data = {
        "method" : "start_animation_playlist",
        "params" : {
            "animations" : animations,
            "color_schemes" : color_schemes,
            "time_delay" : time_delay
        }
    }
    return json.dumps(json_data), False


def send_stop_animation_playlist_command():
    json_data = {
        "method" : "stop_animation_playlist",
        "params" : {},
    }
    return json.dumps(json_data), False


def send_download_music_command():
    url = input("Enter a Youtube URL: ")
    title = input("Enter the title: ")
    artist = input("Enter the artist: ")

    json_data = {
        "method": "download_song",
        "params" : {
            "url" : url,
            "title" : title,
            "artist" : artist,
        },
    }
    return json.dumps(json_data), False


def get_songs():
    """Constructs `get_songs` command"""
    json_data = {
        "method" : "get_songs",
        "params" : {}
    }
    return json.dumps(json_data), True


def get_palettes():
    """Constructs `get_palettes` command"""
    json_data = {
        "method" : "get_palettes",
        "params" : {}
    }
    return json.dumps(json_data), True


def get_effects():
    """Constructs `get_effects` command"""
    json_data = {
        "method" : "get_effects",
        "params" : {}
    }
    return json.dumps(json_data), True


def construct_json(command) -> str:
    """
    Constructs a JSON-RPC request based on the provided command. This
    will call an associated method that returns the associated JSON-RPC
    request as a string.

    :param command: command id lookup. Ultimately points to function to call
    :return: JSON-RPC request string
    """
    commands = {
        1: send_set_light_command,
        2: send_trigger_effect_command,
        3: send_set_pallete_command,
        4: send_start_music_sync_command,
        5: send_stop_music_sync_command,
        6: send_start_animation_playlist_command,
        7: send_stop_animation_playlist_command,
        8: send_download_music_command,
        9: get_songs,
    }
    return commands[command]()

def recv_all(s):
    # Receive the response from the server
    data = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed before receiving valid JSON.")
            data += chunk
            json_data = json.loads(data.decode('utf-8'))
            break  # Exit the loop once JSON is successfully parsed
        except json.JSONDecodeError:
            # Continue receiving more data if JSON is incomplete
            continue
    return json_data


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        global CHRISTMAS_PALETTES
        global ANIMATION_OPTIONS
        global SONG_OPTIONS
        s.connect((HOST, PORT))  # Connect to the server
        print(f"Connected to server at {HOST}:{PORT}")

        palette_command, _ = get_palettes()
        s.sendall(palette_command.encode('utf-8'))
        CHRISTMAS_PALETTES = recv_all(s)["result"]

        effects_command, _ = get_effects()
        s.sendall(effects_command.encode('utf-8'))
        ANIMATION_OPTIONS = recv_all(s)["result"]

        songs_command, _ = get_songs()
        s.sendall(songs_command.encode('utf-8'))
        SONG_OPTIONS = recv_all(s)["result"]

        while True:
            command = pick_command()
            if command.lower() == 'exit':
                print("Exiting...")
                break

            # Send the command to the server
            json_command, is_getter = construct_json(int(command))
            s.sendall(json_command.encode('utf-8'))
            json_data = recv_all(s)

            if is_getter:
                SONG_OPTIONS = json_data["result"]
                print(f"Succesfully received data from server")
            else:
                print(f"Received from server:\n{json.dumps(json_data, indent=4)}")

if __name__ == "__main__":
    main()
