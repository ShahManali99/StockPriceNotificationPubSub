Use the following commands to run the deployed application:
Go to the parent directory and run:
1. docker compose build
2. docker compose up

To kill a server, you can either use Docker UI or you can use the following command:
docker kill <container_name>
eg docker kill server3.

To run frontend, simply copy the link for index.html and paste it on your browser.

In order to evaluate the system performance, you need to change measure = True in all the server.py files
in server1, server2 and server3 directories.
