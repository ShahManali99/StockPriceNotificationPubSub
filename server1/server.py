import socket
import sys
import random
from _thread import *
from threading import Timer, Thread
import time

measure = False
servers_connected = []
subscribers = []
stocks = ['Google', 'Apple', 'Nvidia', 'Microsoft', 'Costco']
subscribed_stocks = []
subscriptions = {}
generated_events = dict()
flags = dict()
price = {
    'Google': [180],
    'Apple':  [194],
    'Nvidia': [1120],
    'Microsoft': [480],
    'Costco': [820]
}

current_leader = 3
leader_alive = True
heartbeat_interval = 5
heartbeat_timeout = 10

# For measurement
numberOfEvents = [10000]
currNumberOfEventsIndex = 0
currNumberOfEvents = 0
start = 0
samples = [1]
currSamples = 0
sampleList = []

servers = {
    "server1": {"id": 1, "host": "server1", "port": 8040},
    "server2": {"id": 2, "host": "server2", "port": 8041},
    "server3": {"id": 3, "host": "server3", "port": 8042}
}

def connect_subscriber(connection, client_name, stock):
    while True:
        flags[client_name] = 0
        subscribe(client_name, stock)
        subscription_info = 'You are subscribing to this stock: ' + str(subscriptions[client_name])
        connection.send(subscription_info.encode())

        while True:
            if flags[client_name] == 1:
                notify(connection, client_name)

def middleware_server_sender(connection, server_name):
    while True:
        flags[server_name] = 0
        subscriptions[server_name] = stocks
        subscription_info = 'You are subscribing to this stock: ' + str(subscriptions[server_name])
        try:
            connection.send(subscription_info.encode())
        except:
            test=1

        while True:
            if flags[server_name] == 1:
                notify(connection, server_name)

def middleware_server_receiver(connection, server_name):
    global leader_alive
    while True:
        try:
            server_data = connection.recv(2048).decode()
            if server_data:
                p = server_data.split('-')
                if len(p) == 2:
                    stock = p[0]
                    update = p[1]
                    publish(stock, update, 0)
                p = server_data.split('-')
                if len(p) == 2 and p[0] == 'leader':
                    print(f"Leader election message received: {server_data}")
                    global current_leader
                    if int(p[1]) > current_leader:
                        current_leader = int(p[1])
                        leader_alive = True
                        connection.send("OK".encode())
                    else:
                        connection.send("NOK".encode())
            leader_alive = True
        except socket.error:
            leader_alive = False
            break

def subscribe(name, stock):
    stocks = stock.split(',')
    subscriptions[name] = stocks
    for s in stocks:
        if s not in subscribed_stocks:
            subscribed_stocks.append(s)

def generate_updates():
    global measure
    while not subscribed_stocks:
        continue
    stock = random.choice(subscribed_stocks)
    msg_list = price[stock]
    update = str(msg_list[0] + random.choice(list(range(-10,10))))
    if not measure:
        print("Generated Update: ", stock, update)
    publish(stock, update, 1)

def publish(stock, update, indicator):
    update = stock + ' - ' + update
    if indicator == 1:
        for name, subscribed_stocks in subscriptions.items():
            if stock in subscribed_stocks:
                if name in generated_events:
                    generated_events[name].append(update)
                else:
                    generated_events.setdefault(name, []).append(update)
                flags[name] = 1
    else:
        for name, subscribed_stocks in subscriptions.items():
            if name in subscribers:
                if stock in subscribed_stocks:
                    if name in generated_events:
                        generated_events[name].append(update)
                    else:
                        generated_events.setdefault(name, []).append(update)
                    flags[name] = 1
    if not measure:
        t = Timer(random.choice(list(range(4, 6))), generate_updates)
        t.start()

def notify(connection, name):
    if name in generated_events:
        for msg in generated_events[name]:
            msg = msg + str("\n")
            try:
                connection.send(msg.encode())
            except:
                test=1
        del generated_events[name]
        flags[name] = 0
    global currNumberOfEventsIndex
    global currNumberOfEvents
    global start
    global samples
    global currSamples
    if name == subscribers[0] and measure:
        if start == 0:
            start = time.time()
        if currNumberOfEvents < numberOfEvents[currNumberOfEventsIndex]:
            currNumberOfEvents = currNumberOfEvents + 1
            generate_updates()
        else:
            timeTaken = time.time() - start
            sampleList.append(timeTaken)
            currNumberOfEvents = 0
            start = 0
            if currSamples < samples[currNumberOfEventsIndex]:
                currSamples = currSamples + 1
                generate_updates()
            else:
                print(f"Total time for {numberOfEvents[currNumberOfEventsIndex]} events: ", sum(sampleList)/len(sampleList))
                if currNumberOfEventsIndex < len(numberOfEvents) - 1:
                    currNumberOfEventsIndex = currNumberOfEventsIndex + 1
                    currSamples = 0
                    sampleList.clear()
                    generate_updates()

def start_election(server_name):
    global current_leader
    print(server_name + " starting leader election")
    my_id = servers[server_name]["id"]
    higher_servers = [server for server in servers.values() if server["id"] > my_id]
    for server in higher_servers:
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.connect((server["host"], server["port"]))
            connection.send(f"leader-{my_id}".encode())
            response = connection.recv(2048).decode()
            if response == "OK":
                return
        except Exception as e:
            # print(f"Failed to connect to {server['host']}: {e}")
            continue
    current_leader = my_id
    print(f"{server_name} has been elected as leader")
    for server in servers.values():
        if server["id"] < my_id:
            try:
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                connection.connect((server["host"], server["port"]))
                connection.send(f"leader-{my_id}".encode())
            except Exception as e:
                print(f"Failed to notify {server['host']}: {e}")

def send_heartbeat(server_name):
    global current_leader, leader_alive
    while True:
        time.sleep(heartbeat_interval)
        if current_leader == servers[server_name]["id"]:
            leader_alive = True
            continue
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.connect((servers[f"server{current_leader}"]["host"], servers[f"server{current_leader}"]["port"]))
            connection.send("heartbeat".encode())
        except socket.error:
            leader_alive = False
        if not leader_alive:
            print("Leader failed. Starting election ...")
            start_election(server_name)

def main(server_name):
    global current_leader, leader_alive, servers_connected
    server = servers[server_name]

    host = server["host"]
    port = server["port"]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    print(f"{server_name} bind to port:", port)
    s.listen(5)
    print(f"{server_name} listening to new connections")
    t = Timer(random.choice(list(range(4, 6))), generate_updates)
    t.start()

    for server_info in servers.values():
        if server_info["host"] == server_name:
            continue
        if server_info["host"] in servers_connected:
            continue
        server_host = server_info["host"]
        server_port = server_info["port"]
        ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ss.connect((server_host, server_port))
            ss.send(server_name.encode())
            response = connection.recv(2048).decode()
            if response == "OK":
                start_new_thread(middleware_server_receiver, (ss,server_host))
                start_new_thread(middleware_server_sender, (ss,server_host))
                servers_connected.append(server_info["host"])
        except:
            continue

    start_new_thread(send_heartbeat, (server_name,))
    start_election(server_name)

    while True:
        connection, addr = s.accept()
        data = connection.recv(2048).decode()

        if data and data != "heartbeat":
            print("Welcome", data)
        l = data.split('-')
        if l[0] == 'c':
            subscribers.append(l[1])
            start_new_thread(connect_subscriber, (connection, l[1], l[2]))
        if l[0] in ('server1', 'server2', 'server3'):
            connection.send("OK".encode())
            if l[0] not in servers_connected:
                start_new_thread(middleware_server_sender, (connection, l[0]))
                start_new_thread(middleware_server_receiver, (connection, l[0]))
        if l[0] == 'leader':
            print(f"Leader election message received: {data}")
            if int(l[1]) > servers[server_name]["id"]:
                current_leader = int(l[1])
                print("New leader: ", current_leader)
                leader_alive = True
            elif int(l[1]) < servers[server_name]["id"]:
                connection.send("OK".encode())
                start_election(server_name)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python server.py <server_name>")
        sys.exit(1)

    server_name = sys.argv[1]
    if server_name not in servers:
        print(f"Unknown server name {server_name}. Expected one of {list(servers.keys())}.")
        sys.exit(1)

    main(server_name)