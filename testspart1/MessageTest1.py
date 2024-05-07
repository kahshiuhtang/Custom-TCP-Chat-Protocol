import random

from .BasicTest import *


class MessageTest1(BasicTest):
    def set_state(self):
        self.num_of_clients = 1
        self.client_stdin = {"client1": 1}
        self.input = [("client1", "msg 1 client1 Hello\n")]
        self.last_time = time.time()