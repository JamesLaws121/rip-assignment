import argparse
import json
import select
import socket
import sys
import time

import threading



"""
Notes on potential issues
Current timer might have flaw where reading will muck up how often it is polled
this probably doesn't matter
can probably be fixed with some threading and better scheduling
"""


"""
To run code use:

python rip.py config
            ^^filename^^

I made it add the .txt might change this later

Current implementation initialises routing table from the config file this is not correct
A router should only be added to the routing table when a packet is received from the router

So we are going to start by doing a broadcast to all neighbouring routers

Need to add check to see if metric on both side of route are same

Need to perform validity checks on incoming packets

"""


class RipDaemon:
    def __init__(self, config_name):
        """ Class to create and manage a RIP daemon """
        print("Daemon created")
        daemon_alive = True

        """ Parse config file for valid id, ports and outputs"""
        daemon_input = RipDaemon.read_config(config_name)

        if daemon_input == -1:
            self.end_daemon()

        self.router_id, self.input_ports, self.outputs = daemon_input

        # Setup sockets to receive data with
        self.input_sockets = self.socket_setup(self.input_ports)

        # Generic socket used to send updates
        self.output_socket = self.input_sockets[0]

        # router_id : [port, metric, timer]
        self.routing_table = {self.router_id: [0, 0, 0]}

        # Ports ready to read from
        self.readable = []
        # Used to tell if the port can be written to
        self.writeable = []
        # Need to look into this
        self.exceptional = []

        # Used to tell when to send advts
        self.advt_counter = 0
        # Interval to check output status
        self.timeout = 10
        # Time timer started
        self.start = 0

        self.display_config_details()

        while daemon_alive is True:
            # Main loop
            readable, writeable, exceptional = select.select(self.input_sockets, [], [], self.timeout)

            # Might need to make this use multithreading

            if len(readable) != 0:
                # Read from sockets
                # threading.Thread(target=self.read_input, args=readable)
                self.read_input(readable)

            if len(writeable) != 0:
                # Probably won't want this one
                print("Write to sockets")

            if len(exceptional) != 0:
                print("check exceptional")

            if self.check_timer():
                self.send_updates()

            print("")
            self.display_details()
            print("")

    def display_config_details(self):
        print("***********************\n")
        print("***** Config file *****")

        print(f"Router ID: {self.router_id}")

        print(f"Input ports: {[port for port in self.input_ports]} \n")

        print("Outputs: ")
        for output in self.outputs:
            print(f"Port: {output[0]} Id: {output[1]} Metric {output[2]}")

        print("\n***********************\n")

    def display_details(self):
        print("***********************\n")
        print("**** Routing table ****")
        for router_id, value in self.routing_table.items():
            print(f"Router Id: {router_id}")
            print(f"Port: {value[0]}")
            print(f"Metric: {value[1]}")
            print("")

        print("***********************\n")

    def check_timer(self):
        """ Checks if it's time to send router adverts"""

        if self.start < time.time():
            self.start = time.time() + self.timeout
            return True
        return False

    def update_table_timers(self):
        """ Update the time since an entry was last updated"""
        print("do this later")
        print("not important")
        self.display_details()

    def send_updates(self):
        """ Sends the routers table to its neighbour routers """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        encoded_table = self.encode_table()
        for output in self.outputs:
            sock.sendto(encoded_table, ("127.0.0.1", output[0]))

    def read_input(self, readable):
        """ Reads updates from routers """
        for sock in readable:
            data, addr = sock.recvfrom(1024)
            data, next_hop = RipDaemon.decode_table(data)
            self.update_table(data, next_hop)

        return data

    def encode_table(self):
        """ Creates the packet to be sent"""
        # Header is 4 bytes
        # An entry is 20 bytes
        packet_size = 4 + len(self.routing_table) * 20
        packet = bytearray(packet_size)
        packet[0:4] = bytearray([self.router_id])

        peer_ids = [{key: self.routing_table[key]} for key in self.routing_table]
        count = 0
        for i in range(4, packet_size, 20):
            entry = json.dumps(peer_ids[count])
            packet[i: i + 20] = bytearray(entry.encode("utf-8"))
            count += 1

        # data = json.dumps({"data": [self.routing_table, self.router_id]})
        # encoded_table = bytes(data, encoding="utf-8")
        # router_id = bytes(str(self.router_id), encoding="utf-8")

        return packet

    @staticmethod
    def decode_table(data):
        """ Converts data received to usable format"""
        # decoded_data = data.decode('utf-8')
        # received_table, next_hop = json.loads(decoded_data)["data"]
        # Converts the dictionary keys to integers
        # received_table = {int(id): received_table[id] for id in received_table}
        # return received_table, next_hop

        router_table = {}
        peer_id = int.from_bytes(data[0:4], "little")

        count = 0
        for i in range(4, len(data), 20):
            entry = data[i: i + 20].decode('utf-8').split('\0')[0]
            router_table.update(json.loads(entry))
            count += 1

        router_table = {int(id): router_table[id] for id in router_table}

        return router_table, peer_id

    def update_table(self, new_data, peer_id):
        """ Updates the routers table with the table received from a peer"""
        # peer_id is the router the data came from
        # new_data is data received from peer

        if peer_id not in self.routing_table:
            self.add_peer(peer_id)

        for id in new_data:
            if id not in self.routing_table:
                # Add new entry to table
                self.routing_table[id] = [self.routing_table[peer_id][0], (new_data[id][1] + self.routing_table[peer_id][1]), 0]
            else:
                # Update existing entry in table
                new_metric = new_data[id][1] + self.routing_table[peer_id][1]
                if new_metric < self.routing_table[id][1]:
                    self.routing_table[id] = [self.routing_table[peer_id][0], new_metric, 0]

    def add_peer(self, peer_id):
        """ Adds a peer router to the routing table """
        for output in self.outputs:
            if output[2] == peer_id:
                port = output[0]
                metric = output[1]

        self.routing_table[peer_id] = [port, metric, 0]

    def end_daemon(self):
        print("Destroying daemon")
        self.display_details()
        sys.exit()

    @staticmethod
    def socket_setup(input_ports):
        """ Creates udp sockets """
        input_sockets = []

        for port in input_ports:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.bind(("127.0.0.1", port))
            input_sockets.append(udp_socket)

        return input_sockets

    @staticmethod
    def read_config(config_name):
        """ Reads the configuration file """

        config_file = open(config_name)

        config = config_file.readlines()
        config_dict = {}
        for line in config:
            variable, value = line.split(":")

            # Cleans up any newlines and whitespace
            config_dict[variable] = [value.strip() for value in value.split(",")]

        router_id = config_dict["router_id"][0]
        input_ports = config_dict["input_ports"]
        outputs = config_dict["outputs"]

        formatted_config = RipDaemon.convert_config(router_id, input_ports, outputs)

        if formatted_config[0] != 1:
            print(formatted_config[1])
            return -1

        router_id, input_ports, outputs = formatted_config[1]

        RipDaemon.validate_config(router_id, input_ports, outputs)

        return router_id, input_ports, outputs

    @staticmethod
    def convert_config(router_id, input_ports, outputs):
        """Transforms the raw data from the configuration file into usable data"""

        if router_id.isdigit():
            router_id = int(router_id)
        else:
            return -1, "Router id is an invalid value"

        input_ports = [int(port) if port.isdigit() else None for port in input_ports]
        if None in input_ports:
            return -1, "An input port is an invalid value"

        correct_output = []
        for output_string in outputs:
            output = output_string.split("-")

            if len(output) == len(output_string):
                return 3

            if output[0].isdigit() and output[1].isdigit() and output[2].isdigit():
                output_port = int(output[0])
                output_metric = int(output[1])
                output_id = int(output[2])
            else:
                return -1, "An output value is invalid"

            correct_output.append((output_port, output_metric, output_id))

        return 1, (router_id, input_ports, correct_output)

    @staticmethod
    def validate_config(router_id, input_ports, outputs):
        """ Checks  all values in config for correctness"""

        max_port = 64000
        max_id = 64000

        if 1 < router_id < max_id:
            return -1, "Router id not in integer range"
        if len(set(input_ports)) != len(input_ports):
            return -1, "2 or more input ports have the same port number"
        for i_port in input_ports:
            if i_port < 1024 or i_port > max_port:
                return -1, "An input port number has not in range"
        for output in outputs:
            if output[0] in input_ports:
                return -1, "Output port number is the same as Input port number"
            if output[0] < 1024 or i_port > max_port:
                return -1, "An output port number has not in range"
            # check if output[1,2] are ints
        return 1, "All good"


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument('filename', help="The name of the config file to use.")

    args = argParser.parse_args()
    config_input = args.filename + ".txt"

    if config_input is None:
        print("No config file name was given")
    else:
        rip_daemon = RipDaemon(config_input)
