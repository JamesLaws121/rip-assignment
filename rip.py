# import socket
import sys, getopt
import select
import argparse


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

        self.read_config(config_name)

            # Uncomment this to test your code
        #self.validate_config()

        self.create_sockets()

        # Ports to wait on input
        self.readable = []
        # Output ports
        self.writeable = []
        # Need to look into this
        self.exceptional = []

        return

        while daemon_alive is True:
            # Main loop
            readable, writeable, exceptional = select.select(self.input_ports, [], [])

            if len(readable) != 0:
                print("Read from sockets")

            if len(writeable) != 0:
                # Probably wont want this one
                print("Write to sockets")

            if len(exceptional) != 0:
                print("check exceptional")

            print("ALIVE")

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
        
        for i_port in self.input_ports:
            try:
                hold = int(i_port) #needs proper variable name
            except ValueError:
                return 2
            correct_input.append(hold)
        self.input_ports = correct_input

        for o_port in self.outputs:
            hold = o_port.split("-")
            if len(hold) == len(o_port):
                return 3
            if len(hold[0]) != 4:
                return 4
            try:
                hold[0] = int(hold[0])
            except ValueError:
                return 4
            if len(hold[1]) != 1:
                return 5
            try:
                hold[1] = int(hold[1])
            except ValueError:
                return 5
            if len(hold[2]) != 4:
                return 6
            try:
                hold[2] = int(hold[2])
            except ValueError:
                return 6
            correct_output.append((hold[0], hold[1], hold[2]))
        self.outputs = correct_output


    def validate_config(self):
        """ Checks  all values in config for correctness"""

        """Error codes:
                    1: Router id not in integer range
                    2: 2 or more input ports have the same port number
                    3: An input port number has not in range
                    4: Output port number is the same as Input port number
                    5: An output port number has not in range
                    6: """

        

        """ For future maybe try to reduce magic numbers eg max_port instead of 64000"""

        max_port = 64000
        max_id = 64000

        if self.router_id > 1 and self.router_id < max_id: 
            return 1
        if len(set(self.input_ports)) != len(self.input_ports):
            return 2
        for i_port in self.input_ports:
            if i_port < 1024 or i_port > max_port:
                return 3
        for o_port in self.outputs:
            output = o_port.split("-")
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
