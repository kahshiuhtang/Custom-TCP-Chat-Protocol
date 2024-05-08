'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import logging
import threading
import queue
import time
import random


class Server:
    '''
    This is the main Server Class. You will  write Server code inside this class.
    '''

    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.usernames = dict()
        self.window = window
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(filename='./logs/server.log',
                            encoding='utf-8', level=logging.DEBUG)
        self.recv_pkts = dict()  # Mappings from seqno to pkts
        self.pkt_types = dict()  # Mappings from seqno to pkt type
        self.recv_starts = dict()  # Mappings from seqno to pkts
        self.recv_ends = dict()  # Mappings from seqno to pkts
        self.sent_pkts = dict()  # Mappings from seqno to pkts
        self.recv_acks = set()
        self.completed_pkts = set()
        self.queue = queue.Queue()
        self.mutex = threading.Lock()

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.

        '''
        self.logger.debug('Starting Server')
        T = threading.Thread(target=self.recv_packet)
        T.daemon = True
        T.start()
        try:
            while True:
                self.logger.debug('[SERVER]: Waiting for new packet')
                data, client_address = self.queue.get()
                segments = data.split()
                self.logger.debug('[SERVER]: Recieved packet:')
                self.logger.debug(segments)
                self.logger.debug("FROM: ")
                self.logger.debug(client_address)
                msg = segments
                if msg[0] == "join":
                    self.logger.debug('[MSG]: Join')
                    if len(msg) < 3:
                        self.logger.debug(
                            '[ERROR]: Join messsage has less than 3 items')
                        continue
                    name = msg[2]
                    if len(self.usernames) == util.MAX_NUM_CLIENTS:
                        self.logger.debug('[SERVER]: Max clients hit in JOIN')
                        full_serv_msg = util.make_message(
                            msg_type="err_server_full", msg_format=2)
                        self.send_packet(
                            msg=full_serv_msg, client_address=client_address)
                        continue
                    if name in self.usernames.keys():
                        self.logger.debug('[SERVER]: Name found in usernames')
                        used_msg = util.make_message(
                            msg_type="err_username_unavailable", msg_format=2)
                        self.send_packet(
                            msg=used_msg, client_address=client_address)
                    else:
                        self.logger.debug(
                            'Adding this username to list of usernames')
                        self.usernames.update({name: client_address})
                        print("join: " + str(name))
                elif msg[0] == "request_users_list":
                    self.logger.debug('[MSG]: Request Users List')
                    user_string = self.generate_users()
                    users_msg = util.make_message(
                        msg_type="response_users_list", msg_format=3, message=user_string)
                    self.send_packet(
                        msg=users_msg, client_address=client_address)
                    username = self.get_username(client_address=client_address)
                    print("request_users_list: " + str(username))
                elif msg[0] == "send_message":
                    self.send_all_msgs(msg, client_address)
                elif msg[0] == "disconnect":
                    self.logger.debug('[MSG]: Disconnect')
                    if len(msg) < 3:
                        self.logger.debug(
                            '[ERROR]: Invalid message content for disconnect')
                        continue
                    name = msg[2]
                    self.handle_disconnect(name)
                else:
                    self.logger.debug('[MSG]: Unknown Message')
                    unknown_msg = util.make_message(
                        msg_type="err_unknown_message", msg_format=2)
                    self.send_packet(
                        msg=unknown_msg, client_address=client_address)
                    username = self.get_username(client_address=client_address)
                    self.handle_disconnect(username)
                    print("disconnected: " + username + " sent unknown command")
        except Exception as e:
            self.logger.debug("[SERVER]: Ending server due to exception.")
            self.logger.debug(e)
            self.sock.close()

    def send_all_msgs(self, msg, client_address):
        self.logger.debug('[MSG]: Send Message')
        num_recipients = int(msg[2])
        recipients = msg[3: 3 + num_recipients]
        sent_to = set()
        msg_to_send = " ".join(msg[3 + num_recipients:])
        self.logger.debug('[Server]: Msg To Send')
        self.logger.debug(msg_to_send)
        self.logger.debug('[Server]: Recipients')
        self.logger.debug(recipients)
        sender = self.get_username(client_address=client_address)
        print("msg: " + str(sender))
        for idx in range(0, num_recipients):
            user = recipients[idx]
            if user in sent_to:
                self.logger.debug(
                    '[Server]: Duplicate address specified, ' + str(user))
                pass
            else:
                sent_to.add(user)
                if user not in self.usernames.keys():
                    print("msg: " + str(sender) +
                          " to non-existent user " + user)
                else:
                    T = threading.Thread(target=self.send_msg_to_user, args=(user, sender, msg_to_send))
                    T.daemon = True
                    T.start()

    def send_packet(self, msg, client_address):
        chunks = []
        for i in range(0, len(msg), util.CHUNK_SIZE):
            chunks.append(msg[i:min(i+util.CHUNK_SIZE, len(msg))])
        starting_seq_num = random.randint(10000, 10000000)
        pkts_sent = 0
        start_pkt = util.make_packet(
            msg_type="start", msg="", seqno=starting_seq_num + pkts_sent)
        self.sock.sendto(str(start_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
        time.sleep(0.05)
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            self.sock.sendto(str(start_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
            time.sleep(0.5)
        pkts_sent += 1
        seqs = []
        self.mutex.acquire()
        for _, chunk in enumerate(chunks):
            data_pkt = util.make_packet(msg_type="data",
                                        msg=chunk, seqno=starting_seq_num + pkts_sent)
            self.sent_pkts.update({starting_seq_num + pkts_sent: data_pkt})
            self.sock.sendto(str(data_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
            seqs.append(starting_seq_num + pkts_sent + 1)
            self.sock.sendto(str(data_pkt).encode('utf-8'),
                                     (client_address[0], client_address[1]))
            pkts_sent += 1
        self.mutex.release()
        all_found = False
        time.sleep(0.05)
        while all_found == False:
            all_found = True
            for seq in seqs:
                if seq not in self.recv_acks:
                    all_found = False
                    data_pkt = self.sent_pkts[seq - 1]
                    self.sock.sendto(str(data_pkt).encode('utf-8'),
                                     (client_address[0], client_address[1]))
            if all_found == False:
                time.sleep(0.5)
        end_pkt = util.make_packet(msg_type="end",
                                   msg="", seqno=starting_seq_num + pkts_sent)
        self.sock.sendto(str(end_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
        time.sleep(0.05)
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            self.sock.sendto(str(end_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
            time.sleep(0.5)

    def recv_packet(self):
        while True:
            # Maybe use client address instead of seq_no's
            data, client_address = self.sock.recvfrom(2048)
            self.logger.debug('[PKT]: Received Packet')
            decoded_msg = data.decode('utf-8')
            msg_type, seq_no, data, checksum = util.parse_packet(decoded_msg)
            # print(seq_no)
            seq_no = int(seq_no)
            self.logger.debug(
                '[PKT]: Checking that packet checksum is valid for ' + str(seq_no))
            if util.validate_checksum(decoded_msg):
                self.logger.debug('[PKT]: Packet is valid.')
                if msg_type == "start":
                    self.logger.debug(
                        '[PKT]: Received START Packet' + str(seq_no))
                    self.mutex.acquire()
                    self.pkt_types.update({seq_no: "start"})
                    self.recv_pkts.update({seq_no: data})
                    self.mutex.release()
                    self.send_ack(seq_no + 1, client_address)
                elif msg_type == "data":
                    self.logger.debug(
                        '[PKT]: Received DATA Packet' + str(seq_no))
                    self.mutex.acquire()
                    self.pkt_types.update({seq_no: "data"})
                    self.recv_pkts.update({seq_no: data})
                    self.mutex.release()
                    self.send_ack(seq_no + 1, client_address)
                elif msg_type == "end":
                    self.logger.debug(
                        '[PKT]: Received END Packet' + str(seq_no))
                    self.mutex.acquire()
                    self.pkt_types.update({seq_no: "end"})
                    self.recv_pkts.update({seq_no: data})
                    self.mutex.release()
                    current_msg = self.get_msg_from_seqs(seq_no)
                    self.logger.debug('[PKT]: End Packet' + str(seq_no))
                    if current_msg == "":
                        continue
                    self.logger.debug(
                        '[PKT]: Received Full Packet With all ACKS')
                    self.send_ack(seq_no + 1, client_address)
                    self.queue.put(
                        (str(current_msg), client_address))
                    self.logger.debug(
                        "[SERVER]: Completed message, " + str(current_msg))
                elif msg_type == "ack":
                    self.logger.debug('[PKT]: Received ACK' + str(seq_no))
                    self.mutex.acquire()
                    self.recv_acks.add(seq_no)
                    self.mutex.release()

    def get_msg_from_seqs(self, seq_no):
        current_msg = ""
        curr_seq = seq_no
        self.mutex.acquire()
        while curr_seq in self.pkt_types.keys():
            self.logger.debug('[MSG_FROM_SEQS]: Looking for' + str(curr_seq))
            current_msg = self.recv_pkts[curr_seq] + current_msg
            if self.pkt_types[curr_seq] == "start":
                break
            curr_seq -= 1
        if curr_seq not in self.pkt_types or self.pkt_types[curr_seq] != "start":
            self.logger.debug('[MSG_FROM_SEQS]: Hmm... missing packets')
            self.mutex.release()
            return ""
        if curr_seq in self.completed_pkts:
            self.logger.debug(
                '[MSG_FROM_SEQS]: Already have processed this completed packet, will not send upward')
            self.mutex.release()
            return ""
        self.completed_pkts.add(curr_seq)
        self.mutex.release()
        return current_msg

    def send_ack(self, seqno, client_address):
        ack_pkt = util.make_packet(msg_type="ack",
                                   msg="", seqno=seqno)
        self.sock.sendto(str(ack_pkt).encode('utf-8'),
                         (client_address[0], client_address[1]))

    def send_msg_to_user(self, user, sender, msg_to_send):
        address, port = self.usernames[user]
        msg_content = "1 " + sender + " " + msg_to_send
        send_msg_user = util.make_message(
            msg_type="forward_message", msg_format=4, message=msg_content)
        self.send_packet(msg=send_msg_user, client_address=(address, port))

    def generate_users(self):
        num_users = len(self.usernames)
        user_string = ""
        for name in sorted(self.usernames.keys()):
            user_string += name + " "
        if user_string != "":
            user_string = user_string[:len(user_string) - 1]
        user_string = str(num_users) + " " + user_string
        return user_string

    def handle_disconnect(self, name):
        self.logger.debug("[SERVER]: Handling disconnect for user " + name)
        if name in self.usernames.keys():
            del self.usernames[name]
        else:
            self.logger.debug(
                "[SERVER]: Error, unable to disconnect this user")
        print("disconnected: " + str(name))

    def get_username(self, client_address):
        for username in self.usernames.keys():
            address, port = self.usernames[username]
            if address == client_address[0] and port == client_address[1]:
                return username
        return ""

# Do not change below part of code


if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=", "window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT, WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
