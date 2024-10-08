'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util
import time
import logging


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
        self.logger = logging.getLogger(__name__) # Set up logging, could give some issues if no log folder is included
        logging.basicConfig(filename='./logs/client_' + str(username) +'.log', encoding='utf-8', level=logging.DEBUG)

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message. 
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        self.send_join() # Send that initial join
        while True:
            message = input("") # Wait for input
            if message.lower() == 'quit':
                self.logger.debug('[INPUT_MSG]: Quit')
                self.exit_client() # Want to exit if we ever get the quit command
                break
            input_words = message.split() # Split up input string and take out the command
            cmd = input_words[0].lower()

            if cmd == "msg":
                self.logger.debug('[INPUT_MSG]: Msg')
                msg_content = self.generate_msg_string(input_words=input_words) # Extract out the message (users and message)
                send_msg = util.make_message("send_message", 4, msg_content)
                pack = util.make_packet(msg=send_msg)
                self.sock.sendto(pack.encode('utf-8'), (self.server_addr, self.server_port))
            elif cmd == "list":
                self.logger.debug('[INPUT_MSG]: List')
                list_msg = util.make_message("request_users_list", 2)
                pack = util.make_packet(msg=list_msg)
                self.sock.sendto(pack.encode('utf-8'), (self.server_addr, self.server_port))
            elif cmd == "help":
                self.logger.debug('[INPUT_MSG]: Help')
                self.print_help()
            else:
                self.logger.debug('[INPUT_MSG]: Unknown message')
                print("incorrect userinput format")
                pass

    def generate_msg_string(self, input_words):
        '''
        From the list of input words, extract out the users and actual message

        '''
        msg_content = input_words[1] + " "
        for entry_count in range(0, int(input_words[1])): # Extract out the intended end users
            msg_content += input_words[2 + entry_count] + " "
        actual_msg = " ".join(input_words[int(input_words[1]) + 2:]) # Take the message out 
        msg_content = msg_content + actual_msg # Concatenate together users and message
        return msg_content
    
    def send_join(self):  
        '''
        Send the initial join packet to the server

        '''    
        join_msg = util.make_message("join", 1, self.username)
        pack = util.make_packet(msg=join_msg)
        self.sock.sendto(pack.encode('utf-8'), (self.server_addr, self.server_port))
    
    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        try:
            while True:
                data, client_address = self.sock.recvfrom(1024)
                self.logger.debug('[RECV_MSG]: packet')
                decoded_data = data.decode('utf-8')
                segments = decoded_data.split("|") # Splitting out the message into an array of strings
                self.logger.debug(segments)
                msg = segments[2].split()
                if msg[0] == "response_users_list":
                    self.logger.debug('[RECV_MSG]: response_users_list')
                    sent_message_whole = segments[2].split() # Take out the list of users and print it out
                    comb_msg = " ".join(sent_message_whole[3:])
                    print("list: " + comb_msg)
                elif msg[0] == "forward_message":
                    self.logger.debug('[RECV_MSG]: forward_message')
                    sent_message_whole = segments[2].split() # Extracting the message that has been sent and from who
                    sender = sent_message_whole[3]
                    comb_msg = " ".join(sent_message_whole[4:])
                    print("msg: " + sender +": " + comb_msg)
                elif msg[0] == "err_unknown_message":
                    self.logger.debug('[RECV_MSG]: err_unknown_message')
                    print("disconnected: server received an unknown command")
                    self.exit_client() # Disconnect since we don't know what has gone wrong
                    return
                elif msg[0] == "err_server_full":
                    self.logger.debug('[RECV_MSG]: err_server_full')
                    print("disconnected: server full")
                    self.exit_client() # Disconnect since we don't know what has gone wrong
                    return
                elif msg[0] == "err_username_unavailable":
                    self.logger.debug('[RECV_MSG]: err_username_unavailable')
                    print("disconnected: username not available")
                    self.exit_client() # Disconnect since we don't know what has gone wrong
                    return
                else:
                    self.logger.debug('[RECV_MSG]: Unknown message sent')
        except:
              self.logger.debug("[SERVER]: Timeout reached. Moving on.")

    def exit_client(self):
        disconnect_msg = util.make_message("disconnect", 1, self.username) # Want to send a disconnect to the server
        pack = util.make_packet(msg=disconnect_msg)
        self.sock.sendto(pack.encode('utf-8'), (self.server_addr, self.server_port))
        self.logger.debug("[SERVER]: Just sent disconnect packet, will it make it")
        time.sleep(0.5) # This will stop some issues with test case stopping too early I think
        print("quitting")

    def print_help(self):
        '''
        Copied from below, prints out the help statement

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
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
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
