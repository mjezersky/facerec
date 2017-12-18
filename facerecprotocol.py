import socket


class FacerecProtocol():
    def __init__(self):
        self.serversock = None
        self.sock = None
        self.clientAddr = None
        self.chunksize = 512
        self.msgMaxLen = 10000000 # max 10MB payload

    def connect(self, host, port):
        addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(addr)

    def accept(self):
        clientsock, addr = self.serversock.accept()
        self.sock = clientsock
        self.clientAddr = addr

    def bind(self, host, port):
        addr = (host, port)
        self.serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversock.bind(addr)

    def listen(self, num):
        self.serversock.listen(num)

    def send(self, msg):
        msglen = len(msg)
        data = str(msglen)+"#"
        self.sock.send(data)
        print "sending", msglen

        total = 0
        for i in range(int(msglen/self.chunksize)+1):
            currIndex = i*self.chunksize
            data = msg[currIndex:currIndex+self.chunksize]
            total += len(data)
            self.sock.send( data )
        print "sent", total
            

    def recv(self):
        received = ""
        numberCharLimit = 30
        payloadSize = 0
        counter = 0
        # recv payload size
        while 1:
            counter += 1
            data = self.sock.recv(1)
            if data == "":
                return None
            if data == "#":
                payloadSize = int(received)
                break
            received += data
            if counter > numberCharLimit:
                raise Exception("FacerecProtocol - size number length reached.")

        # recv payload

        print "receiving", payloadSize

        data = ""
	recvd = 0
	while recvd < payloadSize:
		data += self.sock.recv(1)
		recvd += 1        

        print "done", len(data)

        return data

    def sendB64String(self, s):
        self.send(s.encode("base64"))

    def recvB64String(self):
        return self.recv().decode("base64")

    def sendfile(self, filename):
        f = open(filename, "rb")
        data = f.read()
        f.close()
        

    def close(self):
        try: self.sock.close()
        except: pass
        if self.serversock != None:
            try: self.serversock.close()
            except: pass



if __name__ == "__main__":
    x = FacerecProtocol()
    x.connect("localhost", 2105)
    f = open("test.jpg", "rb")
    data = f.read()
    f.close()
    x.send(data)
    x.close()
