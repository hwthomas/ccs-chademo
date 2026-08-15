import can

line = "06,00,00,00,B3,01,FF,00"
items = line.split(',')

print("all items [0:7) = ", items)

b2 = ''.join(items[4:6])

print("b2 = ", b2)
ib2 = int(b2, 16)
print("int(b2,16) = ", ib2)

data = bytearray(8)                # build data bytes as <bytearray>
for i in range(0,7):
    data[i] = int(items[i], 16)     # all data items are int's
    
print("type of data is ", type(data), "\ndata = ", data)

print("type_b2 = ", type(b2), b2)

val = int(b2, 16)
print("val bs = ", b2)

ba = data[4]*256 + data[5]
print("type data[4] is ", type(data[4]))

print(type(ba), ba)

#val_ba = int(ba, 16)
#print("val_ba = ", val_ba)
