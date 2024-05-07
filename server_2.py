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
        self.queue = queue.Queue()

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
                if len(segments) < 3:
                    self.logger.debug('[ERROR]: Wrong sized packet')
                    continue
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
                        pkt = util.make_packet(msg=full_serv_msg)
                        self.sock.sendto(pkt.encode('utf-8'),
                                         (client_address[0], client_address[1]))
                        continue
                    if name in self.usernames.keys():
                        self.logger.debug('[SERVER]: Name found in usernames')
                        used_msg = util.make_message(
                            msg_type="err_username_unavailable", msg_format=2)
                        pkt = util.make_packet(msg=used_msg)
                        self.sock.sendto(pkt.encode('utf-8'),
                                         (client_address[0], client_address[1]))
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
                    pkt = util.make_packet(msg=users_msg)
                    self.logger.debug(pkt)
                    self.sock.sendto(pkt.encode('utf-8'),
                                     (client_address[0], client_address[1]))
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
                    used_msg = util.make_message(
                        msg_type="err_unknown_message", msg_format=2)
                    pkt = util.make_packet(msg=used_msg)
                    self.sock.sendto(pkt.encode('utf-8'),
                                     (client_address[0], client_address[1]))
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
                    self.send_msg_to_user(user, sender, msg_to_send)

    def send_packet(self, msg, client_address):
        chunks = []
        for i in range(0, len(msg), util.CHUNK_SIZE):
            chunks.append(msg[i:min(i+util.CHUNK_SIZE, len(msg))])
        starting_seq_num = random.randint(10000, 10000000)
        pkts_sent = 0
        start_pkt = util.make_packet(
            msg_type="start", msg="", seqno=starting_seq_num + pkts_sent)
        pkts_sent += 1
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            time.sleep(0.5)
            self.sock.sendto(str(start_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
        seqs = []
        for _, chunk in enumerate(chunks):
            data_pkt = util.make_packet(msg_type="data",
                                        msg=chunk, seqno=starting_seq_num + pkts_sent)
            self.sent_pkts.update({starting_seq_num + pkts_sent: data_pkt})
            self.sock.sendto(str(data_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))
            seqs.append(starting_seq_num + pkts_sent + 1)
            pkts_sent += 1
        all_found = False
        while all_found == False:
            time.sleep(0.5)
            all_found = True
            for seq in seqs:
                if seq not in self.recv_acks:
                    all_found = False
                    data_pkt = self.sent_pkts[seq - 1]
                    self.sock.sendto(str(data_pkt).encode('utf-8'),
                                     (client_address[0], client_address[1]))
        end_pkt = util.make_packet(msg_type="end",
                                   msg="", seqno=starting_seq_num + pkts_sent)
        while starting_seq_num + pkts_sent + 1 not in self.recv_acks:
            time.sleep(0.5)
            self.sock.sendto(str(end_pkt).encode('utf-8'),
                             (client_address[0], client_address[1]))

    def recv_packet(self):
        while True:
            # Maybe use client address instead of seq_no's
            data, client_address = self.sock.recvfrom(2048)
            decoded_msg = data.decode('utf-8')
            msg_type, seq_no, data, checksum = util.parse_packet(decoded_msg)
            # print(seq_no)
            seq_no = int(seq_no)
            if util.validate_checksum(decoded_msg):
                if msg_type == "start":
                    self.pkt_types.update({seq_no: "start"})
                    self.recv_pkts.update({seq_no: data})
                    self.send_ack(seq_no + 1, client_address)
                elif msg_type == "data":
                    self.pkt_types.update({seq_no: "data"})
                    self.recv_pkts.update({seq_no: data})
                    self.send_ack(seq_no + 1, client_address)
                elif msg_type == "end":
                    self.pkt_types.update({seq_no: "end"})
                    self.recv_pkts.update({seq_no: data})
                    current_msg = self.get_msg_from_seqs(seq_no)
                    if current_msg == "":
                        continue
                    self.send_ack(seq_no + 1, client_address)
                    self.queue.put(
                        (str(current_msg), client_address))
                    self.logger.debug(
                        "[SERVER]: Completed message, " + str(current_msg))
                elif msg_type == "ack":
                    self.recv_acks.add(seq_no)

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
        pkt = util.make_packet(msg=send_msg_user)
        self.logger.debug(pkt)
        self.logger.debug(address)
        self.logger.debug(port)
        self.sock.sendto(pkt.encode('utf-8'), (address, port))

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
