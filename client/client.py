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
    print("6. Get songs")
    print("7. Show Palettes")
    print("8. Show Animation/Effects List")
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
    return json.dumps(json_data)



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
    return json.dumps(json_data)


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
    return json.dumps(json_data)


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
    song = int(song_ids[choice])

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
    return json.dumps(json_data)

def send_stop_music_sync_command():
    """Constructs `stop_songs` command"""

    # fill json data
    json_data = {
        "method" : "stop_song",
        "params" : {}
    }
    return json.dumps(json_data)


def get_songs():
    """Constructs `get_songs` command"""
    json_data = {
        "method" : "get_songs",
        "params" : {}
    }
    return json.dumps(json_data)


def get_palettes():
    """Constructs `get_palettes` command"""
    json_data = {
        "method" : "get_palettes",
        "params" : {}
    }
    return json.dumps(json_data)


def get_effects():
    """Constructs `get_effects` command"""
    json_data = {
        "method" : "get_effects",
        "params" : {}
    }
    return json.dumps(json_data)


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
        6: get_songs,
        7: get_palettes,
        8: get_effects,
    }
    return commands[command]()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        global CHRISTMAS_PALETTES
        global ANIMATION_OPTIONS
        global SONG_OPTIONS
        s.connect((HOST, PORT))  # Connect to the server
        print(f"Connected to server at {HOST}:{PORT}")


        s.sendall(get_palettes().encode('utf-8'))
        data = s.recv(4096)
        CHRISTMAS_PALETTES = json.loads(data.decode('utf-8'))["result"]

        s.sendall(get_effects().encode('utf-8'))
        data = s.recv(4096)
        ANIMATION_OPTIONS = json.loads(data.decode('utf-8'))["result"]

        s.sendall(get_songs().encode('utf-8'))
        data = s.recv(4096)
        SONG_OPTIONS = json.loads(data.decode('utf-8'))["result"]

        while True:
            command = pick_command()
            if command.lower() == 'exit':
                print("Exiting...")
                break

            # Send the command to the server
            json_command = construct_json(int(command))
            s.sendall(json_command.encode('utf-8'))

            # Receive the response from the server
            data = s.recv(4096)
            json_data = json.loads(data.decode('utf-8'))

            # Print the JSON data in a nice, readable format
            print(f"Received from server:\n{json.dumps(json_data, indent=4)}")



if __name__ == "__main__":
    main()
