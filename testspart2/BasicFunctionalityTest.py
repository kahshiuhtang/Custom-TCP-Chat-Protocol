import hashlib
import os
import random
from string import ascii_letters
import time
from testspart2 import BasicTest

class BasicFunctionalityTest(BasicTest.BasicTest):
    def set_state(self):
        self.num_of_clients = 4
        self.long_string = ''.join(random.choice(ascii_letters) for i in range(5000))
        self.client_stdin = {"client1": 1, "client2":2, "client3":3, "client4": 4}
        self.input = [  ("client1","list\n"),
                        ("client4","msg 3 client1 client3 client4 Can we cheat?\n"),
                        ("client4", f"msg 3 client1 client3 client4 {self.long_string}\n"),
                        ("client2","msg 4 client1 client2 client3 client4 Hello Dear Friends! Do not cheat.\n")
                     ]
        self.last_time = time.time()
        self.num_of_acks = 8*2 + 2*2 + 4*2 + 5*2 + 2*2 + 5*2
        self.time_interval = 2
    

    def result(self):
        self.result_basic()
        
