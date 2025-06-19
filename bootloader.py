##############################################################################
## Author: Sebastian Tobias Holdt
## Copyright: Technical University of Denmark - 2025
## Comments:
## This file contains the elf parser andbootloader serial sender running on the sending computer
##############################################################################

import sys
import time
import serial
import serial.tools.list_ports

readFile = sys.argv[1]

startCode = 0x00017373.to_bytes(4, 'little')
endCode = 0x00027373.to_bytes(4, 'little')
zeroCode = 0x00037373.to_bytes(4, 'little')

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

def isELF32(fileArray):
  magicBytes = bytearray([0x7F, 0x45, 0x4C, 0x46, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
  return fileArray[0:16] == magicBytes

def isELF64(fileArray):
  magicBytes = bytearray([0x7F, 0x45, 0x4C, 0x46, 0x02, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
  return fileArray[0:16] == magicBytes

def writeELF32(ser, fileArray):
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
    if (secType == 1 and ".comment" not in name and ".debug" not in name): # If type == SHT_PROGBITS. Addr != 0 should be changed to something smarter, but this is to avoid comments. UPDATE: it has been changed to check .comment name. more sections or smarter solution might be needed in the future. 
      content = fileArray[secOffset : secOffset + secSize]
      missingBytes = (-len(content)) % 4
      content += bytes(b'\x00'*missingBytes)
      print("Writing segment: " + name + " at addresses 0x{:02X}".format(addr) + "-0x{:02X}".format(addr + len(content)))
      writeBinary(ser, content, addr)

  print("Starting program at address: 0x{:02X}".format(entryPoint))
  writeEndCode(ser, entryPoint)

def writeELF64(ser, fileArray):
  entryPoint = bytesToInt(fileArray[24:32])
  secHeadOff = bytesToInt(fileArray[40:48])
  secHeadSize = bytesToInt(fileArray[58:60])
  secHeadNum = bytesToInt(fileArray[60:62])
  secHeadStrNdx = bytesToInt(fileArray[62:64])

  strSecHeadOff = secHeadOff + secHeadSize*secHeadStrNdx
  strSec = fileArray[strSecHeadOff : strSecHeadOff + secHeadSize]
  strSecOff = bytesToInt(strSec[24:32])
  strSecSize = bytesToInt(strSec[32:40])
  strTable = fileArray[strSecOff:strSecOff+strSecSize]

  skippedSections = []

  for i in range(secHeadNum):
    headerOffset = secHeadOff + secHeadSize*i
    sec = fileArray[headerOffset : headerOffset + secHeadSize]
    nameIndex = bytesToInt(sec[0:4])
    secType = bytesToInt(sec[4:8])
    addr = bytesToInt(sec[16:24])
    secOffset = bytesToInt(sec[24:32])
    secSize = bytesToInt(sec[32:40])
    name = strTable[nameIndex:].split(b'\x00')[0].decode('ascii')
    if (secType == 1 and ".comment" not in name and ".debug" not in name):
      content = fileArray[secOffset : secOffset + secSize]
      print("Writing segment: " + name + " at addresses 0x{:02X}".format(addr) + "-0x{:02X}".format(addr + len(content)))
      writeBinary(ser, content, addr)
    elif (secType == 8):
      print("Zeroing segment: " + name + " at addresses 0x{:02X}".format(addr) + "-0x{:02X}".format(addr + secSize))
      writeZeroSection(ser, addr, secSize)
    elif (secType != 0 and secType != 2 and secType != 3):
      skippedSections.append(name + "(0x{:X})".format(secType))
  
  print("Skipped sections:", " ".join(skippedSections))

  print("Starting program at address: 0x{:02X}".format(entryPoint))
  writeEndCode(ser, entryPoint)

def writeBinary(ser, binary, wrPtr = 0):
  transmit(ser, startCode)
  transmit(ser, intToBytes(wrPtr))
  transmit(ser, binary)

def writeEndCode(ser, startAddr = 0):
  transmit(ser, endCode)
  transmit(ser, intToBytes(startAddr))

def writeZeroSection(ser, startPtr, length):
  transmit(ser, zeroCode)
  transmit(ser, intToBytes(startPtr))
  transmit(ser, intToBytes(length))

def transmit(ser, buffer):
  ser.write(buffer)

with open(readFile, "rb") as file:
  fileArray = file.read()
  port = getPort()
  try:
    ser = serial.Serial(port, 115200, timeout=3)
  except:
    print("Unable to open Serial Port")
    quit()
  if (isELF32(fileArray)):
    writeELF32(ser, fileArray)
  elif (isELF64(fileArray)):
    writeELF64(ser, fileArray)
  else:
    print("Writing file as binary with entry point 0x0")
    writeBinary(ser, fileArray)
    writeEndCode(ser)
  ser.close()
