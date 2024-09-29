import socket
from time import sleep

SERVER_IP = "192.168.1.30"


def connect_to_server(ip, port=80):
    try:
        # Create a socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to the server
        client_socket.connect((ip, port))
        print(f"Connected to server {ip} on port {port}")
        return client_socket

    except Exception as e:
        print(f"An error occurred: {e}")
    return None


def send_message(client_socket, message):
    # Send some data to the server
    client_socket.sendall(message.encode())

    # Receive data from the server (optional)
    response = client_socket.recv(1024)
    print(f"Received from server: {response.decode()}")

def close_socket(client_socket):
    # Close the connection
    client_socket.close()

if __name__ == "__main__":
    client_socket = connect_to_server(SERVER_IP)

    message = input("Enter message: ")
    while(message.lower() != "quit" and message.lower() != "q"):
        send_message(client_socket, message)
        message = input("Enter message: ")

    close_socket(client_socket)