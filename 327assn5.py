import socket
import ipaddress

serverIP = input('Enter destination IP: ')
if not isinstance(serverIP, str):
    raise ValueError('Must be str')

serverPort = int(input('Enter port: '))
if not isinstance(serverPort, int):
    raise ValueError('Must be int')

maxBytesToReceive = 1024

myTCPsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
myTCPsocket.connect((serverIP, serverPort))
print('Connected.')
while True:
    someData = input('Enter data: ')

    if someData.lower() == 'quit':
        break

    myTCPsocket.send(bytearray(str(someData), encoding='utf-8'))
    serverResponse = myTCPsocket.recv(maxBytesToReceive)
    print('Response:', serverResponse.decode('utf-8'))
    
myTCPsocket.close()
