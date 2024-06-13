import sys
import socket

def main():
    host = "server1"
    backup_host = "server2"
    port = 8040
    backup_port = 8041
    on_backup = False
    subscriber_name = str(sys.argv[1])
    print("Subscriber name:", subscriber_name)
   
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.send(subscriber_name.encode())
        
        while True:
            data = s.recv(2048).decode()
            if not data:
                print("Server has been disconnected.")
                if on_backup:
                    break
                print("Subscriber connecting to backup server: " + backup_host)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((backup_host, backup_port))
                s.send(subscriber_name.encode())
                on_backup = True
            print(data)

    except ConnectionRefusedError:
        print("Connection refused. Make sure the server is running.")

    except Exception as e:
        print("Connection refused. Make sure the server is running.")

    finally:
        s.close()

if __name__ == '__main__':
    main()
