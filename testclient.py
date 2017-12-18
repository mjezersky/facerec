import facerecprotocol as frp

p = frp.FacerecProtocol()
p.connect("10.0.75.2", 9000)


f = open("D:\\skola\\DP - cam\\testfiles\\test5.jpg", "rb")
data1 = f.read()
f.close()

f = open("D:\\skola\\DP - cam\\testfiles\\test6.jpg", "rb")
data2 = f.read()
f.close()

p.send(data1)
p.send(data2)
resp = p.recv()
print resp
raw_input()
