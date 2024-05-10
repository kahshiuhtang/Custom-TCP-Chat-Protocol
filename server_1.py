'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import logging
import threading
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
        self.logger = logging.getLogger(__name__) # Set up logging to files inside a folder called logs
        logging.basicConfig(filename='./logs/server.log', encoding='utf-8', level=logging.DEBUG)

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it.

        '''
        self.logger.debug('Starting Server')
        try:
            while True:
                self.logger.debug('[SERVER]: Waiting for new packet')
                data, client_address = self.sock.recvfrom(1024)
                decoded_data = data.decode('utf-8')
                segments = decoded_data.split("|") # Don't use the function from util to split up the packets
                self.logger.debug('[SERVER]: Recieved packet:')
                self.logger.debug(segments)
                self.logger.debug("FROM: ")
                self.logger.debug(client_address)
                if len(segments) < 3: # Dont think that this is possible, something might have gone wrong
                    self.logger.debug('[ERROR]: Wrong sized packet')
                    continue
                msg = segments[2].split()
                if msg[0] == "join":
                    self.logger.debug('[MSG]: Join')
                    if len(msg) < 3:
                        self.logger.debug('[ERROR]: Join messsage has less than 3 items')
                        continue
                    name = msg[2]
                    if len(self.usernames) == util.MAX_NUM_CLIENTS: # Max client issue
                        self.logger.debug('[SERVER]: Max clients hit in JOIN')
                        full_serv_msg = util.make_message(msg_type="err_server_full", msg_format=2)
                        pkt = util.make_packet(msg=full_serv_msg)
                        self.sock.sendto(pkt.encode('utf-8'), (client_address[0], client_address[1]))
                        continue
                    if name in self.usernames.keys(): # Already existing user
                        self.logger.debug('[SERVER]: Name found in usernames')
                        used_msg = util.make_message(msg_type="err_username_unavailable", msg_format=2)
                        pkt = util.make_packet(msg=used_msg)
                        self.sock.sendto(pkt.encode('utf-8'), (client_address[0], client_address[1]))
                    else: # Otherwise successful
                        self.logger.debug('Adding this username to list of usernames')
                        self.usernames.update({name: client_address})
                        print("join: " + str(name))
                elif msg[0] == "request_users_list":
                    self.logger.debug('[MSG]: Request Users List')
                    user_string = self.generate_users() # Want to get a string of users
                    users_msg = util.make_message(msg_type="response_users_list", msg_format=3, message=user_string)
                    pkt = util.make_packet(msg=users_msg)
                    self.logger.debug(pkt)
                    self.sock.sendto(pkt.encode('utf-8'), (client_address[0], client_address[1]))
                    username = self.get_username(client_address=client_address) # Print out who requested for these users
                    print("request_users_list: " + str(username))
                elif msg[0] == "send_message":
                    self.send_all_msgs(msg, client_address) # Send a message to everyone specified
                elif msg[0] == "disconnect":
                    self.logger.debug('[MSG]: Disconnect')
                    if len(msg) < 3:
                        self.logger.debug('[ERROR]: Invalid message content for disconnect')
                        continue
                    name = msg[2]
                    self.handle_disconnect(name) # Disconnect if they want to be disconnected
                else:
                    self.logger.debug('[MSG]: Unknown Message')
                    used_msg = util.make_message(msg_type="err_unknown_message", msg_format=2)
                    pkt = util.make_packet(msg=used_msg)
                    self.sock.sendto(pkt.encode('utf-8'), (client_address[0], client_address[1]))
                    username = self.get_username(client_address=client_address)
                    self.handle_disconnect(username)
                    print("disconnected: " + username+ " sent unknown command") # Print out who sent an unknown command, might never actually be used
        except Exception as e:
            self.logger.debug("[SERVER]: Ending server due to exception.")
            self.logger.debug(e)
            self.sock.close()

    def send_all_msgs(self, msg, client_address):
        self.logger.debug('[MSG]: Send Message')
        num_recipients = int(msg[2]) # Find out how many people and these people's usernames
        recipients = msg[3: 3 + num_recipients]
        sent_to = set() # Track who we have sent messages to
        msg_to_send = " ".join(msg[3 + num_recipients :]) # Extract out the message we want to send
        self.logger.debug('[Server]: Msg To Send')
        self.logger.debug(msg_to_send)
        self.logger.debug('[Server]: Recipients')
        self.logger.debug(recipients) 
        sender = self.get_username(client_address=client_address) # Get username of sender
        print("msg: " + str(sender))
        for idx in range(0, num_recipients):
            user = recipients[idx]
            if user in sent_to: # If we already sent to soemone, we don't want to send to them again
                self.logger.debug('[Server]: Duplicate address specified, ' + str(user))
                pass
            else:
                sent_to.add(user)
                if user not in self.usernames.keys(): # If this username doesn't exist, print something out
                    print("msg: " + str(sender) + " to non-existent user " + user)
                else:
                    self.send_msg_to_user(user, sender, msg_to_send) # Otherwise everything is good and we send messsage
    
    def send_msg_to_user(self, user, sender, msg_to_send):
        '''
        Send a message to a user

        '''
        address, port = self.usernames[user] # Get the stored address of a user
        msg_content = "1 " + sender + " " + msg_to_send
        send_msg_user = util.make_message(msg_type="forward_message", msg_format=4, message=msg_content)
        pkt = util.make_packet(msg=send_msg_user)
        self.logger.debug(pkt)
        self.logger.debug(address)
        self.logger.debug(port)
        self.sock.sendto(pkt.encode('utf-8'), (address, port)) # Sent them the packet

    def generate_users(self):
        '''
        Generate the list of users that has connected to the server
        
        '''
        num_users = len(self.usernames)
        user_string =  ""
        for name in sorted(self.usernames.keys()):
            user_string += name + " "
        if user_string != "": # If we don't have any users (impossible I think), we shouldn't crash from following statement
            user_string = user_string[:len(user_string) - 1]
        user_string = str(num_users) + " " + user_string # Concatenate everything together
        return user_string

    def handle_disconnect(self, name):
        self.logger.debug("[SERVER]: Handling disconnect for user " + name)
        if name in self.usernames.keys(): # Don't want to crash from disconnecting unconnected user
            del self.usernames[name]
        else: # We should print out a message if there was an error
            self.logger.debug("[SERVER]: Error, unable to disconnect this user")
        print("disconnected: " + str(name))

    def get_username(self, client_address):
        for username in self.usernames.keys(): # Go through all of the usernames and see if the address/port matches and return the user
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
                                   "p:a:w", ["port=", "address=","window="])
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

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
