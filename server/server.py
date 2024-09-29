
import network
import socket
from time import sleep
import machine

ssid = 'Tyrell.com'
password = 'murphy242'


# Function to connect to WLAN
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip

# Function to open a socket
def open_socket(ip):
    address = (ip, 80)
    connection = socket.socket()
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of address
    connection.bind(address)
    connection.listen(1)
    print(f'Server listening on {ip}:80')
    return connection

# Client class to manage connection and communication
class Client:
    def __init__(self, connection):
        self.connection = connection
        self.client = None

    # Accept a new client connection
    def accept_client(self):
        self.client, _ = self.connection.accept()
        print("Client connected")

    # Receive a request from the client
    def receive_request(self):
        if self.client:
            request = self.client.recv(1024)
            if not request:
                return None
            return str(request.decode())  # Decode the received bytes to a string
        return None

    # Send a response to the client
    def send_response(self, response):
        if self.client:
            self.client.send(response.encode())

    # Close the client connection
    def close_client(self):
        if self.client:
            self.client.close()
            self.client = None
            print("Client connection closed")

# Function to serve clients
def serve(connection):
    client_handler = Client(connection)

    while True:
        client_handler.accept_client()  # Accept a new client
        keep_alive = True

        while keep_alive:
            request = client_handler.receive_request()

            if request:
                print(f"Request received: {request}")

                # Check for 'quit' command to end session
                if request.strip().lower() == "quit":
                    response = "Goodbye!"
                    client_handler.send_response(response)
                    keep_alive = False  # Stop handling this client, allow new clients to connect
                else:
                    # Handle regular request
                    response = f"Server received: {request}"
                    client_handler.send_response(response)
            else:
                # If no data is received, close the connection
                keep_alive = False

        client_handler.close_client()  # Close the client connection after finishing the loop

# Main function to run the server
try:
    ip = connect()
    connection = open_socket(ip)
    serve(connection)
except KeyboardInterrupt:
    machine.reset()
