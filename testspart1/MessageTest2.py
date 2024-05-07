import random

from .BasicTest import *


class MessageTest2(BasicTest):
    def set_state(self):
        self.num_of_clients = 1
        self.client_stdin = {"client1": 1, "client2": 2 }
        self.input = [("client1", "msg 1 client2 Hello Client2\n")]
        self.last_time = time.time()