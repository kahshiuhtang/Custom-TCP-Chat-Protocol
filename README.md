# Chat Application with Custom Reliable UDP Protocol

## Part 1: Simple Chat Application

This part describes the application architecture, socket programming, the message protocol, and how the chat application operates.

### 1.1) Application-Server

The application-server is single-threaded and listens for new connections on a specified port. It accepts connections and handles messages sent from each client. The server can handle up to `MAX_NUM_CLIENTS` clients simultaneously. When the limit is reached, any new client attempting to connect is rejected. The server does not store data from disconnected clients and remains alive until explicitly terminated. 

### 1.2) Application-Client

The application-client serves as the interface for users to interact with the chat server. Each client connects with a unique username and can send and receive messages. The client reads user input from standard input and sends messages to the server. If the client encounters an error from the server, it closes the connection and displays a message explaining why.

### 1.3) Socket Programming

To communicate between the client and server over the Internet, we use socket programming. The transport protocol chosen for this assignment is **UDP**. UDP provides no guarantees about message delivery, which will be addressed in Part 2.

Both the server and client will use localhost (`127.0.0.1`) as the IP address, and the server will listen on a fixed port number known to all clients. Clients will choose random open port numbers to create sockets for communication.

### 1.4) Application API and Protocols

#### Sequence of Events

1. The client connects to the server by sending a `join` message.
2. The server registers the client, stores its address, and acknowledges the connection.
3. Clients can send messages to other connected clients via the server.

#### 1.4a) Application API

The client supports the following API functions:

1. **Message**  
   Sends a message to specified clients. The format is:
msg <number_of_users> <username1> <username2> ... <message>


2. **Available Users**  
Lists all connected users (including the client itself) in ascending order:

3. **Help**  
Displays available commands and their formats:


4. **Quit**  
Disconnects from the server and gracefully shuts down:
quit

#### 1.4b) Protocols and Message Format

There are several types of messages exchanged between the client and server. The format for each type is described below:

1. **join** (Type 1)  
Request to join the chat.
- If the server is full, it replies with `ERR_SERVER_FULL`.
- If the username is taken, it replies with `ERR_USERNAME_UNAVAILABLE`.
- If successful, the server registers the user.

2. **request_users_list** (Type 2)  
Client requests the list of users.

3. **response_users_list** (Type 3)  
Server responds with the list of usernames sorted alphabetically.

4. **send_message** (Type 4)  
Client sends a message to other users. If any recipient is invalid, the server will notify the sender.

5. **forward_message** (Type 4)  
The server forwards a message to its intended recipients.

6. **disconnect** (Type 1)  
Client notifies the server that it is disconnecting.

7. **err_unknown_message** (Type 2)  
Server sends this if it receives an unrecognized message from the client.

8. **err_server_full** (Type 2)  
Sent when the server cannot accept new connections.

9. **err_username_unavailable** (Type 2)  
Sent when the requested username is already taken.

#### 1.4c) Packet Formation

In the first part, you don't need to worry about the lower-level details of packets. For now, all messages are sent as strings using UDP with a basic format. Packets consist of:

- **Packet Type:** e.g., data, ack (ignore for Part 1, always `data`).
- **Sequence Number:** (ignore for Part 1, always `0`).
- **Data:** Message content.
- **Checksum:** (ignore for Part 1).

---

## Part 2: Reliable Communication

In this part, you'll implement a reliable transport protocol on top of UDP to ensure reliable message delivery.

### 2.1) Message Sender

The sender takes an input message, splits it into chunks, and sends it using UDP with a checksum for validation. Messages are broken into small packets, each labeled with a sequence number. Each packet must be acknowledged (ACK) by the receiver. If an ACK is not received within 500 milliseconds, the packet is retransmitted.

The connection is initiated by sending a **START** packet, and once the entire message is sent, it is finalized with an **END** packet.

### 2.2) Message Receiver

The receiver stores the incoming message and verifies the checksum for each packet. If the checksum is invalid, the packet is discarded. The receiver sends an ACK for each valid packet, specifying the next expected sequence number. The final packet (END) signifies the end of the message.

### 2.3) Packet Formation

The packet format consists of a header followed by a data chunk. The header includes:
- **Packet Type:** (start, end, data, ack).
- **Sequence Number:** Incremented with each new packet.
- **Data:** Message content.
- **Checksum:** 32-bit CRC for validation.

To initiate communication, the sender begins with a **START** packet followed by data packets. The connection is terminated with an **END** packet. The checksum ensures the integrity of each packet.

---

### Reliable Delivery with Packet Loss

If a packet is lost (no ACK received), the sender retransmits the packet after 500 milliseconds. This process ensures reliable communication in the presence of packet loss, as every message is acknowledged by the receiver.

---

## Running the Application

### Part 1: Basic Chat Application

Start Server
```bash
python3 server_1.py -p <port_num>
```

Start Client
```bash
python3 client_1.py -p <server_port_num> -u <username>
```

### Part 2: Reliable Chat Application

Start Server
```bash
python3 server_2.py -p <port_num>
```Start the Client(s):```

Start Client
```bash
python3 client_2.py -p <server_port_num> -u <username>
```