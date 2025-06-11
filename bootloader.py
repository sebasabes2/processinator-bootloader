import sys
import serial
import serial.tools.list_ports

readFile = sys.argv[1]

startCode = 0x00017373.to_bytes(4, 'little')
endCode = 0x00027373.to_bytes(4, 'little')

def intToBytes(input):
  return input.to_bytes(4, 'little')

def bytesToInt(input):
  return int.from_bytes(input, 'little')

def getPort():
  ports = list(filter(lambda x: "USB Serial Port" in x.description, serial.tools.list_ports.comports()))
  if (len(ports) == 0):
    print("Unable to find Serial Port")
    return
  if (len(ports) != 1):
    print("Found multiple ports:\n" + '\n'.join(map(lambda x: x.description, ports)))
    return
  return ports[0].device

def isELF(fileArray):
  magicBytes = bytearray([0x7F, 0x45, 0x4C, 0x46, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
  return fileArray[0:16] == magicBytes

def writeELF(ser, fileArray):
  entryPoint = bytesToInt(fileArray[24:28])
  secHeadOff = bytesToInt(fileArray[32:36])
  secHeadSize = bytesToInt(fileArray[46:48])
  secHeadNum = bytesToInt(fileArray[48:50])
  secHeadStrNdx = bytesToInt(fileArray[50:52])

  strSecHeadOff = secHeadOff + secHeadSize*secHeadStrNdx
  strSec = fileArray[strSecHeadOff : strSecHeadOff + secHeadSize]
  strSecOff = bytesToInt(strSec[16:20])
  strSecSize = bytesToInt(strSec[20:24])
  strTable = fileArray[strSecOff:strSecOff+strSecSize]
  
  for i in range(secHeadNum):
    headerOffset = secHeadOff + secHeadSize*i
    sec = fileArray[headerOffset : headerOffset + secHeadSize]
    nameIndex = bytesToInt(sec[0:4])
    secType = bytesToInt(sec[4:8])
    addr = bytesToInt(sec[12:16])
    secOffset = bytesToInt(sec[16:20])
    secSize = bytesToInt(sec[20:24])
    name = strTable[nameIndex:].split(b'\x00')[0].decode('ascii')
    if (secType == 1 and name != ".comment"): # If type == SHT_PROGBITS. Addr != 0 should be changed to something smarter, but this is to avoid comments. UPDATE: it has been changed to check .comment name. more sections or smarter solution might be needed in the future. 
      content = fileArray[secOffset : secOffset + secSize]
      missingBytes = (-len(content)) % 4
      content += bytes(b'\x00'*missingBytes)
      print("Writing segment: " + name + " at addresses 0x{:02X}".format(addr) + "-0x{:02X}".format(addr + len(content)))
      writeBinary(ser, content, addr)

  print("Starting program at address: 0x{:02X}".format(entryPoint))
  writeEndCode(ser, entryPoint)

def writeBinary(ser, binary, wrPtr = 0):
  ser.write(startCode)
  ser.write(intToBytes(wrPtr))
  ser.write(binary)

def writeEndCode(ser, startAddr = 0):
  ser.write(endCode)
  ser.write(intToBytes(startAddr))

with open(readFile, "rb") as file:
  fileArray = file.read()
  port = getPort()
  try:
    ser = serial.Serial(port, 115200)
  except:
    print("Unable to open Serial Port")
    quit()
  # Clear Memory:
  # writeBinary(ser, b'\x00'*0x8000, 0)
  if (isELF(fileArray)):
    writeELF(ser, fileArray)
  else:
    writeBinary(ser, fileArray)
    writeEndCode(ser)
  ser.close()
