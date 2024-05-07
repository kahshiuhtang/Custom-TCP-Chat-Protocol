import random

from .BasicTest import *


class ListUsersTest(BasicTest):
    def set_state(self):
        self.num_of_clients = 4
        self.client_stdin = {"client1": 1, "client2": 2, "client3": 3, "client4": 4}
        self.input = [("client1", "list\n"),
                      ("client2", "list\n")
                    ]
        self.last_time = time.time()
