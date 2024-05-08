'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import threading
import os
import util
import time
import logging
import random
import queue


'''
Write your code inside this class.
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen
for incoming messages in this function.
'''


class Client:
    '''
    This is the main Client Class.
    '''

    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.username = username
        self.window_size = window_size
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(filename='./logs/client_' + str(username) +
                            '.log', encoding='utf-8', level=logging.DEBUG)
        self.recv_pkts = dict()  # Mappings from seqno to pkts
        self.pkt_types = dict()  # Mappings from seqno to pkt type
        self.recv_starts = dict()  # Mappings from seqno to pkts
        self.recv_ends = dict()  # Mappings from seqno to pkts
        self.sent_pkts = dict()  # Mappings from seqno to pkts
        self.recv_acks = set()
        self.completed_pkts = set()
        self.mutex = threading.Lock()
        self.queue = queue.Queue()

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        self.send_join()
        while True:
            message = input("")
            if message.lower() == 'quit':
                self.logger.debug('[INPUT_MSG]: Quit')
                self.exit_client()
                break
            input_words = message.split()
            cmd = input_words[0].lower()

            if cmd == "msg":
                self.logger.debug('[INPUT_MSG]: Msg')
                msg_content = self.generate_msg_string(input_words=input_words)
                send_msg = util.make_message("send_message", 4, msg_content)
                self.send_packet(msg=send_msg)
            elif cmd == "list":
                self.logger.debug('[INPUT_MSG]: List')
                list_msg = util.make_message("request_users_list", 2)
                self.send_packet(msg=list_msg)
            elif cmd == "help":
                self.logger.debug('[INPUT_MSG]: Help')
                self.print_help()
            else:
                self.logger.debug('[INPUT_MSG]: Unknown message')
                print("incorrect userinput format")
                pass

    def generate_msg_string(self, input_words):
        msg_content = input_words[1] + " "
        for entry_count in range(0, int(input_words[1])):
            msg_content += input_words[2 + entry_count] + " "
        actual_msg = " ".join(input_words[int(input_words[1]) + 2:])
        msg_content = msg_content + actual_msg
        return msg_content

    def send_join(self):
        join_msg = util.make_message("join", 1, self.username)
        self.send_packet(msg=join_msg)

    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        T = Thread(target=self.recv_packet)
        T.daemon = True
        T.start()
        try:
            while True:
                data, client_address = self.queue.get()
                segments = data.split()
                self.logger.debug('[RECV_MSG]: packet')
                self.logger.debug(segments)
                msg = segments
                if msg[0] == "response_users_list":
                    self.logger.debug('[RECV_MSG]: response_users_list')
                    sent_message_whole = segments
                    comb_msg = " ".join(sent_message_whole[3:])
                    print("list: " + comb_msg)
                elif msg[0] == "forward_message":
                    self.logger.debug('[RECV_MSG]: forward_message')
                    sent_message_whole = segments
                    sender = sent_message_whole[3]
                    comb_msg = " ".join(sent_message_whole[4:])
                    print("msg: " + sender + ": " + comb_msg)
                elif msg[0] == "err_unknown_message":
                    self.logger.debug('[RECV_MSG]: err_unknown_message')
                    print("disconnected: server received an unknown command")
                    self.exit_client()
                    return
                elif msg[0] == "err_server_full":
                    self.logger.debug('[RECV_MSG]: err_server_full')
                    print("disconnected: server full")
                    self.exit_client()
                    return
                elif msg[0] == "err_username_unavailable":
                    self.logger.debug('[RECV_MSG]: err_username_unavailable')
                    print("disconnected: username not available")
                    self.exit_client()
                    return
                else:
                    self.logger.debug('[RECV_MSG]: Unknown message sent')
        except Exception as e:
            self.logger.debug("[Client]: Ran into error on receive: ")
            self.logger.debug(e)

    def send_packet(self, msg):
        chunks = []
        for i in range(0, len(msg), util.CHUNK_SIZE):
            chunks.append(msg[i:min(i+util.CHUNK_SIZE, len(msg))])
        starting_seq_num = random.randint(10000, 10000000)
        pkts_sent = 0
        start_pkt = util.make_packet(
            msg_type="start", msg="", seqno=starting_seq_num + pkts_sent)
        self.sock.sendto(str(start_pkt).encode('utf-8'),
                             (self.server_addr, self.server_port))
        time.sleep(0.05)
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            self.logger.debug('[PKT]: Sending Start Packet')
            time.sleep(0.5)
            self.sock.sendto(str(start_pkt).encode('utf-8'),
                             (self.server_addr, self.server_port))
            
        pkts_sent += 1
        seqs = []
        for _, chunk in enumerate(chunks):
            data_pkt = util.make_packet(msg_type="data",
                                        msg=chunk, seqno=starting_seq_num + pkts_sent)
            self.sent_pkts.update({starting_seq_num + pkts_sent: data_pkt})
            self.sock.sendto(str(data_pkt).encode('utf-8'),
                             (self.server_addr, self.server_port))
            seqs.append(starting_seq_num + pkts_sent + 1)
            self.sock.sendto(str(data_pkt).encode('utf-8'),
                                     (self.server_addr, self.server_port))
            pkts_sent += 1
        all_found = False
        self.logger.debug('[PKT]: Starting to check that all ACKs arrived')
        time.sleep(0.05)
        while all_found == False:
            self.logger.debug('[PKT]: Checking that all ACKS arrived')
            all_found = True
            for seq in seqs:
                if seq not in self.recv_acks:
                    all_found = False
                    self.logger.debug(
                        '[PKT]: ACK Not Arrived: ' + str(seq - 1))
                    data_pkt = self.sent_pkts[seq - 1]
                    self.sock.sendto(str(data_pkt).encode('utf-8'),
                                     (self.server_addr, self.server_port))
            if all_found == False:
                time.sleep(0.5)
        end_pkt = util.make_packet(msg_type="end",
                                   msg="", seqno=starting_seq_num + pkts_sent)
        self.logger.debug('[PKT]: Starting to send END PKT')
        self.sock.sendto(str(end_pkt).encode('utf-8'),
                             (self.server_addr, self.server_port))
        time.sleep(0.05)
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            self.sock.sendto(str(end_pkt).encode('utf-8'),
                             (self.server_addr, self.server_port))
            time.sleep(0.5)
            self.logger.debug('[PKT]: Sending END PKT')

    def recv_packet(self):
        self.logger.debug('[PKT]: Starting to read in packets')
        while True:
            # Maybe use client address instead of seq_no's
            data, client_address = self.sock.recvfrom(2048)
            self.logger.debug('[PKT]: Received a packet')
            decoded_msg = data.decode('utf-8')
            msg_type, seq_no, data, checksum = util.parse_packet(decoded_msg)
            # print(seq_no)
            seq_no = int(seq_no)
            if util.validate_checksum(decoded_msg):
                self.logger.debug('[PKT]: Valid Packet Received')
                if msg_type == "start":
                    self.logger.debug('[PKT]: Start Packet' + str(seq_no))
                    self.pkt_types.update({seq_no: "start"})
                    self.recv_pkts.update({seq_no: data})
                    self.send_ack(seq_no + 1)
                elif msg_type == "data":
                    self.logger.debug('[PKT]: Data Packet' + str(seq_no))
                    self.pkt_types.update({seq_no: "data"})
                    self.recv_pkts.update({seq_no: data})
                    self.send_ack(seq_no + 1)
                elif msg_type == "end":
                    self.logger.debug('[PKT]: End Packet' + str(seq_no))
                    self.pkt_types.update({seq_no: "end"})
                    self.recv_pkts.update({seq_no: data})
                    current_msg = self.get_msg_from_seqs(seq_no)
                    if current_msg == "":
                        continue
                    self.logger.debug('[PKT]: Concatenated MSG together')
                    self.send_ack(seq_no + 1)
                    self.queue.put(
                        (str(current_msg), client_address))
                    self.logger.debug(
                        "[PKT]: Completed message, " + str(current_msg))
                elif msg_type == "ack":
                    self.logger.debug('[PKT]: Received ACK' + str(seq_no))
                    self.recv_acks.add(seq_no)

    def get_msg_from_seqs(self, seq_no):
        current_msg = ""
        curr_seq = seq_no
        while curr_seq in self.pkt_types.keys():
            self.logger.debug('[MSG_FROM_SEQS]: Looking for' + str(curr_seq))
            current_msg = self.recv_pkts[curr_seq] + current_msg
            if self.pkt_types[curr_seq] == "start":
                break
            curr_seq -= 1
        if curr_seq not in self.pkt_types or self.pkt_types[curr_seq] != "start":
            self.logger.debug('[MSG_FROM_SEQS]: Hmm... missing packets')
            return ""
        if curr_seq in self.completed_pkts:
            self.logger.debug(
                '[MSG_FROM_SEQS]: Already have processed this completed packet, will not send upward')
            return ""
        self.completed_pkts.add(curr_seq)
        return current_msg

    def send_ack(self, seqno):
        ack_pkt = util.make_packet(msg_type="ack",
                                   msg="", seqno=seqno)
        self.sock.sendto(str(ack_pkt).encode('utf-8'),
                         (self.server_addr, self.server_port))

    def exit_client(self):
        disconnect_msg = util.make_message("disconnect", 1, self.username)
        self.send_packet(msg=disconnect_msg)
        self.logger.debug(
            "[SERVER]: Just sent disconnect packet, will it make it")
        time.sleep(0.5)
        print("quitting")

    def print_help(self):
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")


# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=", "window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
