# import socket
import time


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

        self.inputs

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


    def validate_config():
        """ Checks  all values in config for correctness"""
        print("check")



    def create_sockets(self):
        """ Creates the UDP sockets """
        print("Create sockets")


rip_daemon = RipDaemon()
