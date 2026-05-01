import socket
import ipaddress

QUERIES = [
    "What is the average moisture inside our kitchen fridges in the past hours, week and month?",
    "What is the average water consumption per cycle across our smart dishwashers in the past hour, week and month?",
    "Which house consumed more electricity in the past 24 hours, and by how much?"
]

serverIP = input('Enter destination IP: ')
serverPort = int(input('Enter port: '))

maxBytesToReceive = 1024

myTCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
myTCPsocket.connect((serverIP, serverPort))
print('Connected.')

print("Allowed queries: ")
for i in QUERIES:
    print("-", i)


while True:
    someData = input("Enter query or 'quit': ")

    if someData.lower() == 'quit':
        break

    if someData not in QUERIES:
        print("Sorry, this query cannot be processed. Please try one of the supported queries.")
        continue

    myTCPsocket.send(someData.encode('utf-8'))
    serverResponse = myTCPsocket.recv(maxBytesToReceive)
    print('Response:', serverResponse.decode('utf-8'))
    
myTCPsocket.close()
