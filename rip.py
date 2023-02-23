# import socket
import time


class RipDaemon:
    def __init__(self):
        """ Class to create and manage a RIP daemon """
        print("Daemon created")

        self.read_config()

        self.create_sockets()

        while True:
            # Main loop
            time.sleep(5)
            print("ALIVE")

    def read_config(self):
        """ Reads the configuration file """
        print("Read config")

    def create_sockets(self):
        """ Creates the UDP sockets """
        print("Create sockets")


rip_daemon = RipDaemon()
