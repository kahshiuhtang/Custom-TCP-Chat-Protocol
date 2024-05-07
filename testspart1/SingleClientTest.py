import random

from .BasicTest import *


class SingleClientTest(BasicTest):
    def set_state(self):
        self.num_of_clients = 1
        self.client_stdin = {"client1": 1}
        self.input = [("client1", "list\n"),
                      ("client1", "msg 1 client1 Hello\n"),
                      ("client1", "list\n")]
        self.last_time = time.time()
