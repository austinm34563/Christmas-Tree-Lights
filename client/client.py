import socket
import json
from client_consts import *

HOST = 'raspberrypi.local'  # Replace with the Raspberry Pi's IP address on the Wi-Fi network
PORT = 65432          # The port used by the server

"""
Helper method to prompt the user to pick a command.

@return Associated command id
"""
def pick_command():
    print("Here are the list of commands:")
    print("1. Set Light")
    print("2. Pick Effect")
    print("3. Pick Pallette")
    return input("Enter command to send to server (or 'exit' to quit): ")


"""
Helper method to allow users to enter hex or dec for colors. Ideally
users will enter colors in 0xRRGGBB format, but the option is there if
they want to ented the value in dec.

@param integer: integer string value
@returns converted string into int
"""
def convert_integer_input(integer: str):
    # Check if the input starts with '0x' or '0X' to identify hex
    return int(integer, 16) \
           if integer.startswith("0x") or integer.startswith("0X") \
           else int(integer)

"""
Prompts user to enter color info. This color info is then sent to the
rasberry pi server via JSON-RPC.

@returns associated JSON-RPC request string
"""
def send_set_light_command():
    color = convert_integer_input(input("Enter a color: "))
    json_data = {
        "method" : "set_light",
        "params" : {
            "color" : str(hex(color))
        }
    }
    return json.dumps(json_data)


"""
Prompts user for color pallete info. Once info is received, the JSON
data is created and returned.

@return associated JSON-RPC request string
"""
def send_trigger_effect_command():

    # present animation IDs
    print()
    for index, effect in enumerate(ANIMATION_EFFECT_NAMES):
        print(f"{index + 1}. {effect}")
    effect = int(input("Enter an animation id from above: "))

    # specify color scheme/palette options
    print("\nPick the following Color Scheme:")
    for index, pallete in enumerate(CHRISTMAS_PALETTE_NAMES):
        print(f"{index + 1}. {pallete}")

    # specifies an option for pre-loaded color on pi server
    print(f"{len(CHRISTMAS_PALETTE_NAMES) + 1}. Default colors loaded on pi server.")

    scheme_choice = abs(int(input("Choose a scheme from the list above: ")))
    scheme = CHRISTMAS_PALETTES[scheme_choice - 1] if scheme_choice <= len(CHRISTMAS_PALETTE_NAMES) else []

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

"""
Prompts user for color pallete info. Once info is received, the JSON
data is created and returned.

@return associated JSON-RPC request string
"""
def send_set_pallete_command():
    print("Pick the following Pallete:")
    for index, pallete in enumerate(CHRISTMAS_PALETTE_NAMES):
        print(f"{index + 1}. {pallete}")
    pallete_choice = int(input("Choose a pallete from the list above: "))
    if pallete_choice > len(CHRISTMAS_PALETTE_NAMES) or pallete_choice <= 0:
        print("Invalid coice, defaulting to 1")
        pallete_choice = 1
    json_data = {
        "method" : "set_pallete",
        "params" : {
            "pallete" : CHRISTMAS_PALETTES[pallete_choice - 1]
        }
    }
    return json.dumps(json_data)

"""
Constructs a JSON-RPC request based on the provided command. This
will call an associated method that returns the associated JSON-RPC
request as a string.

@param command: command id lookup. Ultimately points to function to call
@return JSON-RPC request string
"""
def construct_json(command) -> str:
    commands = {
        1: send_set_light_command,
        2: send_trigger_effect_command,
        3: send_set_pallete_command,
    }
    return commands[command]()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))  # Connect to the server
        print(f"Connected to server at {HOST}:{PORT}")

        while True:
            command = pick_command()
            if command.lower() == 'exit':
                print("Exiting...")
                break

            # Send the command to the server
            json_command = construct_json(int(command))
            s.sendall(json_command.encode('utf-8'))

            # Receive the response from the server
            data = s.recv(1024)
            print(f"Received from server: {data.decode('utf-8')}")


if __name__ == "__main__":
    main()
