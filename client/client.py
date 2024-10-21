import socket
import json

HOST = '192.168.1.44'  # Replace with the Raspberry Pi's IP address on the Wi-Fi network
PORT = 65432          # The port used by the server


def pick_command():
    print("Here are the list of commands:")
    print("1. Set Light")
    print("2. Pick Effect")
    return input("Enter command to send to server (or 'exit' to quit): ")

def convert_integer_input(user_input):
    # Check if the input starts with '0x' or '0X' to identify hexadecimal
    if user_input.startswith("0x") or user_input.startswith("0X"):
        return int(user_input, 16)  # Convert from hex to int
    else:
        return int(user_input)  # Convert from decimal to int

def send_set_light_command():
    color = convert_integer_input(input("Enter a color: "))
    json_data = {
        "method" : "set_light",
        "params" : {
            "color" : str(hex(color))
        }
    }
    return json.dumps(json_data)

def send_trigger_effect_command():
    effect = int(convert_integer_input(input("Enter an animation id: ")))
    json_data = {
        "method" : "trigger_effect",
        "params" : {
            "animation_id" : effect
        }
    }
    return json.dumps(json_data)

def construct_json(command) -> str:
    commands = {
        1: send_set_light_command,
        2: send_trigger_effect_command,
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
