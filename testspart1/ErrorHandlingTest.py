import random

from .BasicTest import *


class ErrorHandlingTest(BasicTest):
    def set_state(self):
        self.num_of_clients = 3
        self.client_stdin = {"client1": 1, "client2": 2, "client3": 3}
        self.input = [("client1", "msg 1 client4 Hello\n"),
                      ("client2", "msg 2 client1 client0 Welcome Back!\n"),
                      ("client3", "list_my_friends\n"), ("client2", "quitt\n")]
        self.last_time = time.time()

    def result(self):

        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")

        for client in self.client_stdin.keys():
            if not os.path.exists("client_" + client):
                raise ValueError("No such file %s" % "client_" + client)

        server_out = []
        clients_out = {}

        # Checking Join
        for client in self.client_stdin.keys():
            server_out.append("join: %s" % client)
            clients_out[client] = ["quitting"]
            server_out.append('disconnected: %s'% client)

        # Checking Output of Client Messages
        for inp in self.input_to_check:
            client, message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append("request_users_list: %s" % client)
                clients_out[client].append(
                    "list: %s" % " ".join(sorted(self.client_stdin.keys())))
            elif msg[0] == "msg":
                server_out.append("msg: %s" % client)
                for i in range(int(msg[1])):
                    if msg[i + 2] not in clients_out:
                        server_out.append("msg: %s to non-existent user %s" %
                                          (client, msg[i + 2]))
                    else:
                        clients_out[msg[i + 2]].append(
                            "msg: %s: %s" %
                            (client, " ".join(msg[2 + int(msg[1]):])))
            elif msg[0] not in ["quit", "file"]:
                clients_out[client].append("incorrect userinput format")

        # Checking Clients Output
        for client in clients_out.keys():
            with open("client_" + client) as f:
                lines = list(map(lambda x: x.lower(), f.read().split('\n')))
                for each_line in clients_out[client]:
                    if each_line.lower() not in lines:
                        print("Test Failed: Client output is not correct")
                        return False

        # Checking Sever Output in File
        with open("server_out") as f:
            lines = list(map(lambda x: x.lower(), f.read().split('\n')))
            for each_line in server_out:
                if each_line.lower() not in lines:
                    print("Test Failed: Server Output is not correct")
                    return False
        print("Test Passed")
        return True
