#!/usr/bin/python
import os
import socket
import subprocess
import time
import random
import signal
import util
from testspart1 import MessageTest1, MessageTest2, SingleClientTest, BasicTest, MultipleClientsTest, ErrorHandlingTest, ListUsersTest 


def tests_to_run(forwarder):
    ListUsersTest.ListUsersTest(forwarder, "ListUsersTest")
    MessageTest1.MessageTest1(forwarder, "MessageTest1")
    MessageTest2.MessageTest2(forwarder, "MessageTest2")
    SingleClientTest.SingleClientTest(forwarder, "SingleClient")
    MultipleClientsTest.MultipleClientsTest(forwarder, "MultipleClients")
    ErrorHandlingTest.ErrorHandlingTest(forwarder, "ErrorHandling")

class Forwarder(object):
    def __init__(self, sender_path, receiver_path, port):
        if not os.path.exists(sender_path):
            raise ValueError("Could not find sender path: %s" % sender_path)
        self.sender_path = sender_path

        if not os.path.exists(receiver_path):
            raise ValueError("Could not find receiver path: %s" %
                             receiver_path)
        self.receiver_path = receiver_path

        self.tests = {}  # test object => testName
        self.current_test = None
        self.out_queue = []
        self.in_queue = []
        self.tick_interval = 0.001  # 1ms
        self.last_tick = time.time()
        self.timeout = 6.  # seconds

        # network stuff
        self.port = port
        self.cli_ports = {}
        self.middle = {}  # Man in the Middle Sockets
        self.sender_addr = {}
        self.senders = {}
        self.receiver_port = self.port + 1
        self.receiver_addr = None

    def _tick(self):
        self.current_test.handle_tick(self.tick_interval)
        for p, user in self.out_queue:
            self._send(p, user)
        self.out_queue = []

    def _send(self, packet, user):
        packet.update_packet(seqno=packet.seqno, update_checksum=False)
        self.middle[user].sendto(packet.full_packet, packet.address)

    def register_test(self, testcase, testName):
        assert isinstance(testcase, BasicTest.BasicTest)
        self.tests[testcase] = testName

    def execute_tests(self):
        test_count = 0
        for t in self.tests:
            self.port = random.randint(1000, 65500)
            self.current_test = t
            self.current_test.set_state()
            self.middle = {}
            i = 0
            for client in sorted(self.current_test.client_stdin.keys()):
                self.middle[client] = socket.socket(socket.AF_INET,
                                                    socket.SOCK_DGRAM)
                self.middle[client].settimeout(
                    0.01)  # make this a very short timeout
                self.middle[client].bind(('', self.port - i))
                self.cli_ports[client] = self.port - i
                i += 1
            print(("Testing %s" % self.tests[t]))
            self.start()
            test_count += 1

    def handle_receive(self, message, address, user):
        if address[1] == self.receiver_port and user in self.sender_addr:
            p = Packet(message, self.sender_addr[user])
        else:
            if user not in self.sender_addr:
                self.sender_addr[user] = address
            p = Packet(message, self.receiver_addr)

        self.in_queue.append((p, user))
        self.current_test.handle_packet()

    def start(self):
        self.sender_addr = {}
        self.receiver_addr = ('127.0.0.1', self.receiver_port)
        self.recv_outfile = "server_out"

        recv_out = open(self.recv_outfile, "w")
        receiver = subprocess.Popen(
            ["python3", self.receiver_path, "-p",
             str(self.receiver_port)],
            stdout=recv_out)
        time.sleep(0.2)  # make sure the receiver is started first
        self.senders = {}
        sender_out = {}
        for i in list(self.current_test.client_stdin.keys()):
            sender_out[i] = open("client_" + i, "w")
            self.senders[i] = subprocess.Popen([
                "python3", self.sender_path, "-p",
                str(self.cli_ports[i]), "-u", i
            ],
                                               stdin=subprocess.PIPE,
                                               stdout=sender_out[i])
        try:
            start_time = time.time()
            while None in [self.senders[s].poll() for s in self.senders]:
                for i in list(self.middle.keys()):
                    try:
                        message, address = self.middle[i].recvfrom(4096)
                        self.handle_receive(message, address, i)
                    except socket.timeout:
                        pass
                    if time.time() - self.last_tick > self.tick_interval:
                        self.last_tick = time.time()
                        self._tick()
                    if time.time() - start_time > self.timeout:
                        raise Exception("Test timed out!")
            self._tick()
        except (KeyboardInterrupt, SystemExit):
            exit()
        finally:
            for sender in self.senders:
                if self.senders[sender].poll() is None:
                    self.senders[sender].send_signal(signal.SIGINT)
                sender_out[sender].close()
            receiver.send_signal(signal.SIGINT)
            recv_out.flush()
            recv_out.close()

        if not os.path.exists(self.recv_outfile):
            raise RuntimeError("No data received by receiver!")
        time.sleep(1)
        try:
            self.current_test.result()
        except Exception as e:
            print("Test Failed!",e)


class Packet(object):
    def __init__(self, packet, address):
        self.full_packet = packet
        self.address = address
        self.seqno = 0
        try:
            pieces = packet.split('|')
            self.msg_type, self.seqno = pieces[0:2]
            self.checksum = pieces[-1]
            self.data = '|'.join(pieces[2:-1])
            self.seqno = int(self.seqno)
            assert (self.msg_type in ["start", "data", "ack", "end"])
            int(self.checksum)
            self.bogon = False
        except Exception as e:
            self.bogon = True

    def update_packet(self,
                      msg_type=None,
                      seqno=None,
                      data=None,
                      full_packet=None,
                      update_checksum=True):
        if not self.bogon:
            if msg_type == None:
                msg_type = self.msg_type
            if seqno == None:
                seqno = self.seqno
            if data == None:
                data = self.data

            if msg_type == "ack":
                body = "%s|%d|" % (msg_type, seqno)
                checksum_body = "%s|%d|" % (msg_type, seqno)
            else:
                body = "%s|%d|%s|" % (msg_type, seqno, data)
                checksum_body = "%s|%d|%s|" % (msg_type, seqno, data)
            if update_checksum:
                checksum = util.generate_checksum(checksum_body)
            else:
                checksum = self.checksum
            self.msg_type = msg_type
            self.seqno = seqno
            self.data = data
            self.checksum = checksum
            if full_packet:
                self.full_packet = full_packet
            else:
                self.full_packet = "%s%s" % (body, checksum)

    def __repr__(self):
        return "%s|%s|...|%s" % (self.msg_type, self.seqno, self.checksum)


if __name__ == "__main__":
    import getopt
    import sys

    def usage():
        print("Tests for Chat Application")
        print("-p PORT | --port PORT Base port value (default: 33123)")
        print(
            "-c CLIENT | --client CLIENT The path to Client implementation (default: client.py)"
        )
        print(
            "-s SERVER | --server SERVER The path to the Server implementation (default: server.py)"
        )
        print("-h | --help Print this usage message")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:s:r:",
                                   ["port=", "client=", "server="])
    except:
        usage()
        exit()

    port = random.randint(1000, 65500)
    sender = "client_1.py"
    receiver = "server_1.py"

    for o, a in opts:
        if o in ("-p", "--port"):
            port = int(a)
        elif o in ("-c", "--client"):
            sender = a
        elif o in ("-s", "--server"):
            receiver = a

    f = Forwarder(sender, receiver, port)
    tests_to_run(f)
    f.execute_tests()
