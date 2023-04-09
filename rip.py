import socket
import sys

import select
import argparse
import time
import json



"""
Notes on potential issues
Current timer might have flaw where reading will muck up how often it is polled
this probably dosn't matter
"""


"""
To run code use:

python rip.py config
            ^^filename^^

I made it add the .txt might change this later
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
        self.routing_table = {}
        self.create_table()

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

        print(self.input_sockets)

        while daemon_alive is True:
            # Main loop
            readable, writeable, exceptional = select.select(self.input_sockets, [], [], self.timeout)

            # Might need to make this use multithreading

            if len(readable) != 0:
                print("Read from sockets")
                self.read_input(readable)

            if len(writeable) != 0:
                # Probably won't want this one
                print("Write to sockets")

            if len(exceptional) != 0:
                print("check exceptional")

            if self.check_timer():
                self.send_updates()

            print("ALIVE")
            print("")
            self.display_details()
            print("")

    def display_config_details(self):
        print("***********************\n")

        print("Router ID")
        print(self.router_id)
        print("\n")

        print("Input ports: ")
        for port in self.input_ports:
            print(port)
        print("\n")

        print("Output ports: ")
        for port in self.outputs:
            print(port)
        print("\n")

        print("***********************\n")

    def display_details(self):
        print("***********************\n")
        for router_id in self.routing_table:
            print(router_id)
            print(self.routing_table[router_id])
            print("")

        print("***********************\n")

    def check_timer(self):
        """ Checks if its time to send router adverts"""

        if self.start < time.time():
            self.start = time.time() + self.timeout
            return True
        return False

    def update_table_timers(self):
        """ Update the time since an entry was last updated"""
        print("do this later")
        print("not important")
        self.display_details()

    def create_table(self):
        for output in self.outputs:
            self.routing_table[output[2]] = [output[0], output[1], 0]

    def update_table(self, new_data, peer_id):
        print("Update")
        # peer_id is the router the data came from
        # new_data is data received from peer

        # This block is ugly and needs to be refactored
        print(new_data)
        for id in new_data:
            if id not in self.routing_table:
                self.routing_table[id] = [self.routing_table[peer_id][0], (new_data[id][1] + self.routing_table[peer_id][1]), 0]
            else:
                new = new_data[id][1] + self.routing_table[peer_id][1]
                if new < self.routing_table[id][1]:
                    self.routing_table[id] = [self.routing_table[peer_id][0], new, 0]

    def encode_table(self):
        print("table encoded")

        data = json.dumps({"data": [self.routing_table, self.router_id]})
        return bytes(data, encoding="utf-8")

    def int_keys(self, received_table):
        new_table = {}

        for id in received_table:
            new_table[int(id)] = received_table[id]

        return new_table

    def decode_table(self, data):
        print("table decode")
        decoded_data = data.decode('utf-8')
        received_table, next_hop  = json.loads(decoded_data)["data"]

        received_table = self.int_keys(received_table)

        return received_table, next_hop

    def send_updates(self):
        """ Sends the routers table to its neighbour routers"""
        print(self.routing_table)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for output in self.outputs:
            encoded_table = self.encode_table()
            sock.sendto(encoded_table, ("127.0.0.1", output[0]))

    def read_input(self, readable):
        """ Reads updates from routers"""
        for sock in readable:
            data, addr = sock.recvfrom(1024)
            data, next_hop = self.decode_table(data)
            self.update_table(data, next_hop)

        return data


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

    def end_daemon(self):
        print("Destroying daemon")
        self.display_details()
        sys.exit()


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument('filename', help="config filename")

    args = argParser.parse_args()
    config_imput = args.filename + ".txt"

    if config_imput is None:
        print("No config file name was given")
    else:
        rip_daemon = RipDaemon(config_imput)
