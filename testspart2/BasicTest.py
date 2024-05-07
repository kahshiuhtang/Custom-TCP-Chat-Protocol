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
        self.packet_length_exceeded_limit = 0
        self.num_of_acks = 30
        
    def set_state(self):
        pass

    def handle_packet(self):
        for p,user in self.forwarder.in_queue:
            if len(p.full_packet) > 1500:
                self.packet_length_exceeded_limit += 1
                continue
            # print(p.full_packet)
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
        
        elif time.time() - self.last_time > self.time_interval*4:
            for client in self.forwarder.senders.keys():
                self.forwarder.senders[client].stdin.write("quit\n".encode())
                self.forwarder.senders[client].stdin.flush()
            self.last_time = None
        return

    def result(self):
        print("Test Passed!")
        return True

    def result_basic(self):
        # Check if Output File Exists
        if not os.path.exists("server_out"):
            raise ValueError("No such file server_out")
        
        for client in self.client_stdin.keys():
            if not os.path.exists("client_"+client):
                raise ValueError("No such file %s"% "client_" + client)
        
        # Check Packet Length
        if self.packet_length_exceeded_limit > 0:
            print("Test Failed! Every Packet should be of length < 1500 Bytes")
            return False

        # Check ACK packets
        if self.packets_processed['ack'] < self.num_of_acks:
            print("Test Failed! Some Packets were not acknowledged.")
            return False
        
        # Generating Expected Output
        server_out = []
        clients_out = {}
        num_data_pkts = 0
        files = {"test_file1":[], "test_file2":[]}

        for client in self.client_stdin.keys():
            server_out.append("join: %s" % client)
            clients_out[client] = ["quitting"]
            server_out.append('disconnected: %s' % client)
            num_data_pkts += 2
        
        for inp in self.input_to_check:
            client,message = inp
            msg = message.split()
            if msg[0] == "list":
                server_out.append("request_users_list: %s" % client)
                clients_out[client].append("list: %s" % " ".join(sorted(self.client_stdin.keys())))
                num_data_pkts += 2
            elif msg[0] == "msg":
                server_out.append("msg: %s" % client)
                num_data_pkts += 1
                for i in range(int(msg[1])):
                    if msg[i + 2] not in clients_out:
                        server_out.append("msg: %s to non-existent user %s" % (client,msg[i+2]))
                    else:    
                        clients_out[msg[i + 2]].append("msg: %s: %s" % (client, " ".join(msg[2 + int(msg[1]):])) )
                        num_data_pkts += 1
            elif msg[0] == "file":
                server_out.append("file: %s" % client)
                num_data_pkts += 1
                for i in range(int(msg[1])):
                    if msg[i + 2] not in clients_out:
                        server_out.append("file: %s to non-existent user %s" % (client,msg[i+2]))
                    else:
                        clients_out[msg[i + 2]].append("file: %s: %s" % (client, msg[2 + int(msg[1])]) )
                        files[msg[2+int(msg[1])]].append("%s_%s" % (msg[i+2],msg[2+int(msg[1])]))
                        num_data_pkts += 1

        # Checking Output of Clients Messages
        for client in clients_out.keys():
            lines = []
            with open("client_"+client) as f:
                lines = list(map(lambda x: x.lower(), f.read().split('\n')))
            for each_line in clients_out[client]:
                if each_line.lower() not in lines:
                    print("Test Failed: Client output is not correct",each_line,lines)
                    return False
        
        # Checking Output of Server Messages
        lines = []
        with open("server_out") as f:
            lines = list(map(lambda x: x.lower(), f.read().split('\n')))
        for each_line in server_out:
            if each_line.lower() not in lines:
                print("Test Failed: Server Output is not correct")
                return False
        
        # Checking Files
        for filename in files:
            for each_file in files[filename]:
                if not self.files_are_the_same(each_file, filename):
                    print("Test Failed: File is corrupted/not found")
                    return False
        
        # Check end packets
        if self.packets_processed['end'] < num_data_pkts:
            print("Test Failed! Connections were not terminated by end packet.",num_data_pkts, self.packets_processed)
            return False
        
        # Checking start packets
        if self.packets_processed['start'] < num_data_pkts:
            print("Test Failed! Connections were not started by start packet.")
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
