import hashlib
import os
import time
import util

class BasicTest(object):
    def __init__(self, forwarder,test_name="Basic"):
        self.forwarder = forwarder
        self.forwarder.register_test(self,test_name)
        self.num_of_clients = 0
        self.client_stdin = {}
        self.input = []
        self.input_to_check = []
        self.last_time = time.time()
        self.time_interval = 0.5
        self.packets_processed = {"ack":0,"data":0,"start":0,"end":0}

    def set_state(self):
        pass

    def handle_packet(self):
        for p,user in self.forwarder.in_queue:
            msg_type,a,b,c = util.parse_packet(p.full_packet.decode())
            self.packets_processed[msg_type] += 1
            self.forwarder.out_queue.append((p,user))
        self.forwarder.in_queue = []

    def handle_tick(self, tick_interval):
        if self.last_time == None:
            return
        elif len(self.input) > 0:
            if time.time() - self.last_time > self.time_interval:
                client, inpt = self.input[0]
                self.input_to_check.append((client, inpt))
                self.input = self.input[1:]
                self.forwarder.senders[client].stdin.write(inpt.encode())
                self.forwarder.senders[client].stdin.flush()
                self.last_time = time.time()
        
        elif time.time() - self.last_time > 0.5:
            for client in self.forwarder.senders.keys():
                self.forwarder.senders[client].stdin.write("quit\n".encode())
                self.forwarder.senders[client].stdin.flush()
            self.last_time = None
        return

    def result(self):
        num_of_packets = 0
        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")
        
        for client in self.client_stdin.keys():
            if not os.path.exists("client_"+client):
                raise ValueError("No such file %s"% "client_" + client)
        
        server_out = []
        clients_out = {}

        # Checking Join
        for client in self.client_stdin.keys():
            server_out.append("join: %s" % client)
            clients_out[client] = ["quitting"]
            server_out.append('disconnected: %s' % client)
            num_of_packets += 1
        
        # Checking Output of Client Messages
        for inp in self.input_to_check:
            client,message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append("request_users_list: %s" % client)
                clients_out[client].append("list: %s" % " ".join(sorted(self.client_stdin.keys())))
                num_of_packets += 2
            elif msg[0] == "msg":
                server_out.append("msg: %s" % client)
                num_of_packets += 1
                for i in range(int(msg[1])):
                    clients_out[msg[i + 2]].append("msg: %s: %s" % (client, " ".join(msg[2 + int(msg[1]):])) )
                    num_of_packets += 1
        
        
        # Checking Clients Output
        for client in clients_out.keys():
            with open("client_"+client) as f:
                lines = list(map(lambda x: x.lower(), f.read().split('\n')))
                for each_line in clients_out[client]:
                   # print(each_line)
                    if each_line.lower() not in lines:
                       # print(lines)
                        print("Test Failed: Client output is not correct")
                        return False
        
        # Checking Sever Output in File
        with open("server_out") as f:
            lines = list(map(lambda x: x.lower(), f.read().split('\n')))
            for each_line in server_out:
                #print(each_line)
                if each_line.lower() not in lines:
                    print("Test Failed: Server Output is not correct")
                    #print(lines)
                    return False
        
        print("Test Passed")
        return True

    def files_are_the_same(self, file1, file2):
        return BasicTest.md5sum(file1) == BasicTest.md5sum(file2)

    @staticmethod
    def md5sum(filename, block_size=2**20):
        f = open(filename, "rb")
        md5 = hashlib.md5()
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
        f.close()
        return md5.digest()
