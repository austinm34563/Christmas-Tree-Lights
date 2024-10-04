import socket

HOST = '192.168.1.44'  # Replace with the Raspberry Pi's IP address on the Wi-Fi network
PORT = 65432          # The port used by the server

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))  # Connect to the server
        print(f"Connected to server at {HOST}:{PORT}")

        while True:
            command = input("Enter command to send to server (or 'exit' to quit): ")
            if command.lower() == 'exit':
                print("Exiting...")
                break

            # Send the command to the server
            s.sendall(command.encode('utf-8'))

            # Receive the response from the server
            data = s.recv(1024)
            print(f"Received from server: {data.decode('utf-8')}")

if __name__ == "__main__":
    main()