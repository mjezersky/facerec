import facerecprotocol as frp
import classifier as cls


p = frp.FacerecProtocol()
p.bind("0.0.0.0", 9000)
p.listen(1)

while 1:
    print "Accepting..."
    try:
        p.accept()
    except Exception as err:
        print err
        p.close()
        exit()
    while 1:
        try:
            print "awaiting data..."
            data1 = p.recv()
            if data1 == None:
                break
            print "received", len(data1)
            data2 = p.recv()
            if data2 == None:
                break
            print "received2", len(data2)

            vec1 = cls.getRepFromString(data1)[0]
            vec2 = cls.getRepFromString(data2)[0]
            res = cls.compareVectors(vec1, vec2)
            p.send(str(res))
            
        except Exception as ex:
            print ex
            p.close()
            raw_input()
