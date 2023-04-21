import argparse
import random
import select
import socket
import sys
import time

"""
To run code use:

python rip.py config_name


To Do:
    Task set 1
    Read timers from config
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

        # outputs: format: [[port, metric, id], ...]
        self.router_id, self.input_ports, self.outputs = daemon_input

        # output_routes: Used to match router id to physical port
        # format: {router_id: port}
        self.output_routes = {output[2]: output[0] for output in self.outputs}

        # Setup sockets to receive data with
        self.input_sockets = self.socket_setup(self.input_ports)

        # Generic socket used to send updates
        self.output_socket = self.input_sockets[0]

        # router_id : [next_hop, metric, timeout, garbage_collection]
        self.routing_table = {}

        # Ports ready to read from
        self.readable = []
        # Used to tell if the port can be written to
        self.writeable = []
        # Need to look into this
        self.exceptional = []

        # Interval to send output table
        self.timeout = 10
        # time left to wait until updates
        self.countdown = self.timeout
        # Interval to keep dead router entry's
        self.garbage_time = 5
        # Timestamp for when to next send updates
        self.start = 0

        self.display_config_details()

        while daemon_alive is True:
            # Main loop
            readable, _, _ = select.select(self.input_sockets, [], [], self.countdown)

            if len(readable) != 0:
                self.read_input(readable)

            if self.check_timer():
                self.send_updates()

            self.update_table_timers()
            self.display_details()

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
            print(f"Next hop: {value[0]}")
            print(f"Metric: {value[1]}")
            print(f"Timer: {time.time() - value[2]:.2f}")
            if value[3] != 0:
                print(f"Deleting in: {self.garbage_time - (time.time() - value[3]):.2f}")
        print("***********************\n\n")

    @staticmethod
    def display_received_data(data):
        """ This function is used to look at received data"""
        print("***********************\n")
        print("**** Received table ****")
        for router_id, metric in data.items():
            print(f"Router Id: {router_id}")
            print(f"Metric: {metric}")
        print("***********************\n")

    def check_timer(self):
        """ Checks if it's time to send router adverts"""

        if self.start <= time.time():
            self.countdown = self.timeout * (random.randint(8, 12) / 10)
            self.start = time.time() + self.countdown
            return True
        else:
            self.countdown -= (self.start - time.time()-self.countdown)
        return False

    def update_table_timers(self):
        """ Update the time since an entry was last updated """

        # List of entry's to remove from the table
        to_delete = []

        for router_id, entry in self.routing_table.items():
            if entry[3] != 0:
                if (time.time() - entry[3]) > self.garbage_time:
                    to_delete.append(router_id)
                continue

            if time.time() - entry[2] > self.timeout * 6:
                entry[1] = 16
                entry[3] = time.time()
                self.send_updates()

        for router_id in to_delete:
            del self.routing_table[router_id]

    def send_updates(self):
        """ Sends the routers table to its neighbour routers """
        print("Sending updates")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for router_id, port in self.output_routes.items():
            encoded_table = self.encode_table(router_id)
            sock.sendto(encoded_table, ("127.0.0.1", port))

    def read_input(self, readable):
        """ Reads updates from routers """
        for sock in readable:
            packet_data, addr = sock.recvfrom(1024)
            error, result = RipDaemon.validate_packet(packet_data)
            if error == -1:
                print("***********")
                print("** Error **")
                print(result)
                print("Dropping packet")
                print("***********")
                continue

            table_data, next_hop = RipDaemon.decode_table(packet_data)
            self.update_table(table_data, next_hop)

    @staticmethod
    def validate_packet(data):
        """ Validates the packet that's been sent """
        if len(data) < 4:
            return -1, "Incorrect packet size"
        
        elif int.from_bytes(data[0: 4], byteorder="little") < 0:
            return -1, "Incorrect header"
        
        for i in range(4, len(data), 20):
            '''commented out because messy and not sure if needed'''
            if int.from_bytes(data[i: i + 2], byteorder="little") != 0:
                return -1, "Address family ID must be 0" 

            if int.from_bytes(data[i + 2: i + 4], byteorder="little") != 0:
                return -1, "Bytes 2-4 must be 0's"

            if int.from_bytes(data[i + 4: i + 8], byteorder="little") < 0:
                return -1, "Incorrect router Id"
            
            if int.from_bytes(data[i + 8: i + 16], byteorder="little") != 0:
                return -1, "Bytes 8-16 must be 0's"

            if int.from_bytes(data[i + 16: i + 20], byteorder="little") < 0 or int.from_bytes(data[i + 16: i + 20],
                                                                                              byteorder="little") > 16:
                return -1, "Incorrect Metric"
            
        return 1, "Packet valid"

    def encode_table(self, destination_id):
        """ Creates the packet to be sent """
        # Header is 4 bytes
        # An entry is 20 bytes
        packet_size = 4 + len(self.routing_table) * 20
        packet = bytearray(packet_size)
        packet[0:4] = self.router_id.to_bytes(4, byteorder='little')

        peer_ids = [(key, self.routing_table[key][1]) for key in self.routing_table]

        count = 0
        for i in range(4, packet_size, 20):
            entry = peer_ids[count]
            router_id = entry[0]
            metric = entry[1]

            if self.routing_table[router_id][0] == destination_id and destination_id != router_id:
                metric = 16

            # Address family identifier(2)
            packet[i: i + 2] = bytearray(2)
            # Zero(2)
            packet[i + 2: i + 4] = bytearray(2)
            # Router Id(4)
            packet[i + 4: i + 8] = router_id.to_bytes(4, byteorder='little')
            # Zero(8)
            packet[i + 8: i + 16] = bytearray(8)
            # Metric(4)
            packet[i + 16: i + 20] = metric.to_bytes(4, byteorder='little')
            count += 1

        return packet

    @staticmethod
    def decode_table(data):
        """ Converts data received to usable format"""

        # Table of received data format : {id : metric}
        received_table = {}
        peer_id = int.from_bytes(data[0:4], "little")

        for i in range(4, len(data), 20):
            router_id = int.from_bytes(data[i+4: i+8], "little")
            metric = int.from_bytes(data[i+16:i+20], "little")
            received_table.update({router_id: metric})

        return received_table, peer_id

    def update_table(self, new_data, peer_id):
        """ Updates the routers table with the table received from a peer"""

        if peer_id not in self.routing_table:
            self.add_peer(peer_id)
        else:
            self.routing_table[peer_id][2] = time.time()

        for router_id in new_data:
            if router_id == self.router_id:
                if new_data[router_id] != self.routing_table[peer_id][1]:
                    # If two  directly connected routers have
                    print("Received unexpected route metric")
                    print("Config is incorrectly set up")
                    self.end_daemon()

            metric = new_data[router_id] + self.routing_table[peer_id][1]

            if router_id not in self.routing_table and metric != 16:
                # Add new entry to table
                print(f"Adding entry: {router_id} to the table")
                self.routing_table[router_id] = [peer_id, metric, time.time(), 0]
            else:
                # Update existing entry in table
                new_metric = new_data[router_id] + self.routing_table[peer_id][1]

                if self.routing_table[router_id][0] == peer_id:
                    # Metric of currently used route has changed
                    if new_data[router_id] == 16:
                        self.routing_table[router_id][1] = 16
                        self.routing_table[router_id][3] = time.time()
                        self.send_updates()
                    else:
                        self.routing_table[router_id] = [peer_id, new_metric, time.time(), 0]

                elif new_metric < self.routing_table[router_id][1]:
                    print(f"Updating entry: {router_id} in the table")
                    self.routing_table[router_id] = [peer_id, new_metric, time.time(), 0]

                self.routing_table[router_id][2] = time.time()

    def add_peer(self, peer_id):
        """ Adds a peer router to the routing table """

        for output in self.outputs:
            if output[2] == peer_id:
                metric = output[1]

        self.routing_table[peer_id] = [peer_id, metric, time.time(), 0]

    def end_daemon(self):
        """ Destroy router daemon"""
        print("Destroying daemon")
        RipDaemon.display_details(self.routing_table)
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
            print("** Error **")
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
                return -1, "Incorrect"

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

        return 1, "All good"


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument('filename', help="The name of the config file to use.")
    argParser.add_argument('-e', '--extension', help="Set different extension for config file default txt")

    args = argParser.parse_args()

    extension = "txt"
    if args.extension is not None:
        extension = args.extension
    config_input = args.filename + "." + extension

    if config_input is None:
        print("No config file name was given")
    else:
        rip_daemon = RipDaemon(config_input)
