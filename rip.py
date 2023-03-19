import socket
import sys, getopt
import select
import argparse
import time
import json

"""
To Do
Timers for router entries
    - Add timers to routing_table -- tick
    - make timers count up

Send a bytearray out of the routing table
    - create conversion function
    - create function to covert this back
"""



"""
Current timer has flaw where reading will muck up how often it is polled
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

        """Unique identifire for this router"""
        self.router_id = 0


        """[port, distance, id]"""
        self.outputs = []

        """ Ports to listen on"""
        self.input_ports = []

        """Stores sockets"""
        self.input_sockets = []

        """ router_id : [port, metric, timer]"""
        self.routing_table = {}

        """ Used to tell when to send advts"""
        self.advt_counter = 0

        self.read_config(config_name)

        output = self.convert_config()

        print(output)

        self.validate_config()

        self.create_table()

        self.socket_setup()

        # Ports to wait on input
        self.readable = []
        # Output ports
        self.writeable = []
        # Need to look into this
        self.exceptional = []

        # Time in between sending update things (in seconds)
        self.timeout = 10
        # Time timer started
        self.start = 0

        self.display_config_details()

        print(self.input_sockets)

        while daemon_alive is True:
            # Main loop
            readable, writeable, exceptional = select.select(self.input_sockets, [], [], self.timeout)

            # Might need to make this multithreaded

            if len(readable) != 0:
                print("Read from sockets")
                self.read_input(readable)

            if len(writeable) != 0:
                # Probably wont want this one
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

        if(self.start < time.time()):
            self.start = time.time() + self.timeout
            return True
        return False

    def update_table_timers(self):
        """ Update the time since an entry was last updated"""
        print("do this later")
        print("not important")

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
                if new  < self.routing_table[id][1]:
                    self.routing_table[id] = [self.routing_table[peer_id][0], new, 0]

    def encode_table(self):
        print("table encoded")

        data = json.dumps({"data": [self.routing_table, self.router_id]})
        return(bytes(data, encoding="utf-8"))

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
        # Do later

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




    def socket_setup(self):
        """ Creates udp sockets """
        for port in self.input_ports:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.bind(("127.0.0.1", port))
            self.input_sockets.append(udp_socket)

    def read_config(self, config_name):
        """ Reads the configuration file """

        config_file = open(config_name)

        config = config_file.readlines()
        config_dict = {}
        for line in config:
            variable, value = line.split(":")

            # Cleans up any newlines and whitespace
            config_dict[variable] = [value.strip() for value in value.split(",")]

        self.router_id = config_dict["router_id"][0]
        self.input_ports = config_dict["input_ports"]
        self.outputs = config_dict["outputs"]

    def convert_config(self):
        correct_input = []
        correct_output = []
        """Transforms the raw data from the configuration file into data readable by the validate_config function"""

        """Error codes:
            1: Router id is not a correct id
            2: An input port doesnt have a correct port number
            3: An output port has incorrect syntax
            4: An output port number is incorrect
            5: An outputs metric value is incorrect
            6: An outputs peer router id is incorrect"""
        #todo for clean up:
        #change hold variables to better names
        #maybe do something with error codes i.e. return an error message/make a function to do that
        try:
            self.router_id = int(self.router_id)

        except ValueError:
            return 1

        for i_port_string in self.input_ports:
            i_port = self.validate_int(i_port_string)
            correct_input.append(i_port)
        self.input_ports = correct_input

        for output_string in self.outputs:
            output = output_string.split("-")
            print(output)
            if len(output) == len(output_string):
                return 3

            o_port = self.validate_int(output[0])
            o_r_id = self.validate_int(output[2])
            o_metric = self.validate_int(output[1])
            correct_output.append((o_port, o_metric, o_r_id))
        self.outputs = correct_output
        return 0

    def validate_int(self, value):
        if value.isdigit():
            return int(value)
        #talk to james about making a function that stops process because of error
        #return False

    def validate_config(self):
        """ Checks  all values in config for correctness"""

        """
        Error codes:
            1: Router id not in integer range
            2: 2 or more input ports have the same port number
            3: An input port number has not in range
            4: Output port number is the same as Input port number
            5: An output port number has not in range
            6:
        """

        max_port = 64000
        max_id = 64000

        if self.router_id > 1 and self.router_id < max_id:
            return 1
        if len(set(self.input_ports)) != len(self.input_ports):
            return 2
        for i_port in self.input_ports:
            if i_port < 1024 or i_port > max_port:
                return 3
        for output in self.outputs:
            if output[0] in self.input_ports:
                return 4
            if output[0] < 1024 or i_port > max_port:
                return 5
            #check if output[1,2] are ints
        return 0

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument('filename',help="config filename")

    args = argParser.parse_args()
    config_name = args.filename + ".txt"

    if config_name is None:
        print("No config file name was given")
    else:
        rip_daemon = RipDaemon(config_name)
