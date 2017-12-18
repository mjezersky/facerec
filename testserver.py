import facerecprotocol as frp

p = frp.FacerecProtocol()
p.bind("localhost", 2105)
p.listen(1)

while 1:
    print "Accepting..."
    p.accept()
    while 1:
        try:
            print "awaiting data..."
            data = p.recv()
            if data == None:
                break
            print "received", len(data)
            
            f = open("received.jpg", "wb")
            f.write(data)
            f.close()
            
        except Exception as ex:
            print ex
