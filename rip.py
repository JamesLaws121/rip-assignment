# import socket


class RipDaemon:
    def __init__(self):
        """ Class to create and manage a RIP daemon """
        print("Daemon created")
        daemon_alive = True

        self.read_config()

        self.create_sockets()

        self.readable = []
        self.writeable = []
        self.exceptional = []

        self.inputs = []
        self.outputs = []
        

        while daemon_alive is True:
            # Main loop
            self.readable, self.writeable, self.exceptional = select.select([],[],[])

            if len(self.readable) != 0:
                print("Read from sockets")

            if len(self.writeable) != 0:
                # Probably wont want this one
                print("Write to sockets")

            if len(self.exceptional) != 0:
                print("check exceptional")

            print("ALIVE")

    def read_config(self):
        """ Reads the configuration file """
        print("Read config")

        config_file = open()



    def validate_config(router_ids, inputs_port, output_ports, timers):
        """ Checks  all values in config for correctness"""

        """Error codes:
                    1: Router id not in integer range
                    2: 2 or more input ports have the same port number
                    3: An input port number has not in range
                    4: Output port number is the same as Input port number
                    5: An output port number has not in range
                    6: """
        if router_ids > 1 and router_ids < 64000:
            return 1
        if len(set(inputs_port)) != len(inputs_port):
            return 2
        for i_port in inputs_port:
            if i_port < 1024 or i_port > 64000:
                return 3
        for o_port in output_ports:
            output = o_port.split("-")
            if int(output[0]) in inputs_port:
                return 4
            if int(output[0]) < 1024 or i_port > 64000:
                return 5
            #check if output[1,2] are ints
        return 0
    def create_sockets(self):
        """ Creates the UDP sockets """
        print("Create sockets")


rip_daemon = RipDaemon()
