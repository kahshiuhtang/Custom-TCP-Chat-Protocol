import random

from .BasicTest import *


class MultipleClientsTest(BasicTest):
    def set_state(self):
        self.num_of_clients = 3
        self.client_stdin = {"client1": 1, "client2": 2, "client3": 3}
        self.input = [("client1", "list\n"),
                      ("client1", "msg 1 client2 Hello\n"),
                      ("client3", "list\n"),
                      ("client2", "msg 2 client1 client3 Hi! I am client2.\n"),
                      ("client3", "msg 2 client3 client2 Hi Client2!\n"),
                      ("client3",
                       "msg 4 client1 client2 client3 client1 Hey...\n")]
        self.last_time = time.time()
