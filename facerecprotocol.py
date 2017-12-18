import socket


class FacerecProtocol():
    def __init__(self):
        self.serversock = None
        self.sock = None
        self.clientAddr = None
        self.msgMaxLen = 10000000 # max 10MB payload

    def connect(self, host, port):
        addr = (host, port)
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.connect(addr)

    def accept(self):
        clientsock, addr = self.serversock.accept()
        self.sock = clientsock
        self.clientAddr = addr

    def bind(self, host, port):
        addr = (host, port)
        self.serversock = socket(AF_INET, SOCK_STREAM)
        self.serversock.bind(addr)

    def listen(self, num):
        self.serversock.listen(num)

    def send(self, msg):
        data = str(len(msg))+"#"+msg
        self.sock.send(data)

    def recv(self):
        received = ""
        numberCharLimit = 30
        payloadSize = 0
        counter = 0
        # recv payload size
        while 1:
            counter += 1
            data = self.sock.recv(1)
            if data == "#":
                payloadSize = int(received)
                break
            received += data
            if counter > numberCharLimit:
                raise Exception("FacerecProtocol - size number length reached.")

        # recv payload
        return self.sock.recv(payloadSize)

    def close(self):
        try: self.sock.close()
        except: pass
        if self.serversock != None:
            try: self.serversock.close()
            except: pass
            
