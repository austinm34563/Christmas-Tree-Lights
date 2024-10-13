import socket
import threading
from json_rpc import JsonRpc
from light_control import LightControl
from logger import Logger

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 65432      # Arbitrary non-privileged port
MAX_CLIENTS = 5   # Set the maximum number of concurrent clients

# A lock to synchronize access to the client count
client_count_lock = threading.Lock()
current_clients = 0

# logger info
logger = Logger()
TAG = "Server"

# light info
LED_COUNT = 50
lightControl = LightControl(LED_COUNT)

def handle_client(conn, addr):
    global current_clients
    with conn:
        logger.info(TAG, f"Connected by {addr}")
        with client_count_lock:
            current_clients += 1
            logger.info(TAG, f"Current number of clients: {current_clients}")

        while True:
            data = conn.recv(1024)
            if not data:
                break
            command = data.decode('utf-8').strip()
            logger.info(TAG, f"Received command: {command}")

            json_rpc = JsonRpc(lightControl)
            json_rpc.process_json(command)

            response = f"Executed command: {command}"
            conn.sendall(response.encode('utf-8'))

    with client_count_lock:
        current_clients -= 1  # Decrement the number of current clients
        print(f"Client {addr} disconnected. Current number of clients: {current_clients}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reusing the address
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()  # Accept the connection
            with client_count_lock:
                if current_clients >= MAX_CLIENTS:
                    print(f"Max clients reached. Rejecting connection from {addr}.")
                    conn.close()  # Close the connection if max clients are reached
                else:
                    thread = threading.Thread(target=handle_client, args=(conn, addr))
                    thread.start()  # Start a new thread to handle the client

if __name__ == '__main__':
    main()
