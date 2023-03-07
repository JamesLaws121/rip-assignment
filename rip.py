import socket
import sys, getopt
import select
import argparse
import time

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

        self.router_id = []
        self.input_ports = []

        """[port, distance, id]"""
        self.outputs = []

        """Stores sockets"""
        self.socket_dict = {}

        self.routing_table = {}

        """ Used to tell when to send advts"""
        self.advt_counter = 0

        self.read_config(config_name)

        self.convert_config()

        self.validate_config()


        self.create_sockets()

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

        self.display_details()

        return

        while daemon_alive is True:
            # Main loop
            readable, writeable, exceptional = select.select(self.input_ports, [], [], self.timeout)

            # Might need to make this multithreaded

            if len(readable) != 0:
                print("Read from sockets")

            if len(writeable) != 0:
                # Probably wont want this one
                print("Write to sockets")

            if len(exceptional) != 0:
                print("check exceptional")

            if self.check_timer():
                self.send_updates()

            print("ALIVE")

    def display_details(self):
        print("***********************")

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

        print("***********************")

    def calculate_vector(self):
        return 1

    def create_table(self):
        for output in self.outputs:
            self.routing_table[output[0]] = output[1]

    def update_table(self):
        # Do later
        print("Update")

    def send_updates(self):
        # Do later
        print("Send update")

    def check_timer(self):
        if(self.start < time.time()):
            self.start = time.time() + self.timeout
            return True
        return False

    def socket_setup(self):
        for port in self.input_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket_dict[port] = sock

    def read_config(self, config_name):
        """ Reads the configuration file """
        print("Read config")

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
            try:
                i_port = int(i_port_string) #needs proper variable name
            except ValueError:
                return 2
            correct_input.append(i_port)
        self.input_ports = correct_input

        for output_string in self.outputs:
            output = output_string.split("-")
            if len(output) == len(output_string):
                return 3
            if len(output[0]) != 4:
                return 4
            try:
                output[0] = int(output[0])
            except ValueError:
                return 4
            if len(output[1]) != 1:
                return 5
            try:
                output[1] = int(output[1])
            except ValueError:
                return 5
            if len(output[2]) != 4:
                return 6
            try:
                output[2] = int(output[2])
            except ValueError:
                return 6
            correct_output.append((output[0], output[1], output[2]))
        self.outputs = correct_output


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
            if output[0] in self.inputs_port:
                return 4
            if output[0] < 1024 or i_port > max_port:
                return 5
            #check if output[1,2] are ints
        return 0

    def create_sockets(self):
        """ Creates the UDP sockets """
        print("Create sockets")

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument('filename',help="config filename")

    args = argParser.parse_args()
    config_name = args.filename + ".txt"

    if config_name is None:
        print("No config file name was given")
    else:
        rip_daemon = RipDaemon(config_name)
