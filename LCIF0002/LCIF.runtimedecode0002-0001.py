#  Copyright (c) 2019, Alex Hall
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

#the functions
from multiprocessing.dummy import Pool as ThreadPool
from PIL import Image, ImageDraw # PIL stuff
import math, sys, os, multiprocessing
from time import time
CpuCoreCount = multiprocessing.cpu_count()
# functions for the decoder
def unpackResolutionLCIF0001(bits): # unpacks the resolution from 64 bit binary to 2 numbers
  return (int(bits[0:32],2),int(bits[32:64],2))
def unpackVarLCIF0001(binstack): # turns the entire varstack into readable numbers
  outputData = []
  for i in binstack:
    tup = str(hex(int(i,2))).split("x")[1]
    tup = (6-len(tup))*"0"+tup
    r = int(tup[0:2],16); g = int(tup[2:4],16); b = int(tup[4:6],16)
    outputData.append((r,g,b,255))
  return outputData
def decodeLCIF0001(varstack, inputData, pointer): # decodes instructions 00 and 01, usefull
  instr = inputData[pointer:pointer+2]
  pointer+= 2
  if instr == "00": # 00, variable loading
    instr = inputData[pointer:pointer+1]
    pointer+= 1
    if instr == "0":
      outputData = (varstack[int(inputData[pointer:pointer+4],2)]) # 4 bit variable loading
      pointer+= 4
    elif instr == "1":
      outputData = (varstack[int(inputData[pointer:pointer+8],2)]) # 8 bit variable loading
      pointer+= 8
  elif instr == "01":
    instr = inputData[pointer:pointer+2]
    pointer+= 2
    if instr == "00":
      outputData = ((255,255,255,0)) # blank color
    elif instr == "01":
      instr = inputData[pointer:pointer+8] # monochrome color
      pointer+= 8
      mono = int(instr,2)
      outputData = ((mono,mono,mono,255))
    elif instr == "10": # 12 bit color
      instr = inputData[pointer:pointer+12]
      pointer+= 12
      R, G, B = [int(str(hex(int(instr[i*4:i*4+4],2)))+str(hex(int(instr[i*4:i*4+4],2))).split("x")[1],0) for i in range(3)]
      outputData = (R, G, B, 255)
    elif instr == "11": # 24 bit color
      instr = inputData[pointer:pointer+24]
      pointer+= 24
      R, G, B = [int(instr[i:i+8],2) for i in range(0,24,8)]
      outputData = (R, G, B, 255)
  else:
    return (pointer, False, instr)
  return (pointer, True, outputData)
def decoderecurseLCIF0001(inputData, pointer): # decodes the recurse function
  instr = inputData[pointer:pointer+2]
  pointer+= 2
  if instr == "00":
    instr = inputData[pointer:pointer+8]
    pointer+= 8
    return (int(instr,2), pointer)
  elif instr == "01":
    instr = inputData[pointer:pointer+16]
    pointer+=16
    return (int(instr,2), pointer)
  elif instr == "10":
    instr = inputData[pointer:pointer+32]
    pointer+= 32
    return (int(instr,2), pointer)
  elif instr == "11":
    instr = inputData[pointer:pointer+1]
    pointer+=1
    if instr == "0":
      instr = inputData[pointer:pointer+64]
      pointer+= 64
      return (int(instr,2), pointer)
    elif instr == "1":
      instr = inputData[pointer:pointer+128]
      pointer+= 128
      return (int(instr,2), pointer)
      
 # byte packer and depacker V4 -----------------------------------------------------------------------------------------
def pack(byte): # packs bytes of 1 and 0 into bits
  return int(byte, 2)
def unpack(bits):
  dat = str(bin(bits)).split("b")[1]
  dat = ((8-len(dat))*"0")+dat
  return dat

def fromfile(byte): # unpacks bits into string of 1 and 0
  with ThreadPool(CpuCoreCount) as pool:
    byte = "".join(pool.map(unpack, byte))
  return byte
def tofile(outputData): # takes the string of 1 and 0 and packs it into byte objects
  outputData = outputData+(((8-len(outputData))%8)*"1")
  outputData = [outputData[i*8:i*8+8] for i in range(int(len(outputData)/8))]
  with ThreadPool(CpuCoreCount) as pool:
    outputData = bytes(pool.map(pack, outputData))
  return outputData
  
# some encoder stuffs

# ############################
# DECODER START

def LCIF0001decode(file):
  print(f"\ndecoding {file}")
  with open(file,"rb") as txt:
    binD = txt.read(8)
    if binD == b"LCIF0001":
      print("Confirmed correct filetype")
      txt.seek(0)
      binD = txt.read()
    else:
      txt.close()
      print("Does not Support this filetype/version number, this decoder only decodes for LCIF-0001")
      input()
      raise TypeError
  inputData = fromfile(binD) # unpacks to bytedata
  resolution = unpackResolutionLCIF0001(inputData[64:128]) # decodes the resolution
  outputData = []
  print("Converted to bytes")

  pointer = 128
  binstack = []
  while pointer != 128+(256*24): # reads the varstack
    binstack.append(inputData[pointer:pointer+24])
    pointer+=24
  varstack = unpackVarLCIF0001(binstack)
  print("loaded varstack")

  readingData = True
  while readingData: # this thing just does all the instruction reading, instr = instruction btw
    tryfor = decodeLCIF0001(varstack,inputData,pointer)
    pointer = tryfor[0]
    if tryfor[1]:
      outputData.append(tryfor[2])
    else:
      instr = tryfor[2]
      if instr == "10":
        tryfor = decoderecurseLCIF0001(inputData,pointer)
        pointer = tryfor[1]
        recurseColor = decodeLCIF0001(varstack,inputData,pointer)
        pointer = recurseColor[0]
        if recurseColor[1]:
          for i in range(tryfor[0]):
            outputData.append(recurseColor[2])
        else:
          print("file is not encoded properly")
          input()
          raise RuntimeError
      elif instr == "11":
        readingData = False
  print("Decoded to raw, encoding to png")
  print(len(outputData))
  
  image = Image.new("RGBA", (resolution[0], resolution[1]), "white")
  col = ImageDraw.Draw(image)
  for y in range(resolution[1]+1):
    for x in range(resolution[0]+1):
     try:
      col.point([x,y], outputData[x+y*resolution[0]])
     except IndexError:
       pass
  image.save(".".join(file.split(".")[:-1])+"(1).png")
  print("Finished")

###################### 0002

def unpackResolution(bits,sitty): # unpacks the resolution from 64 bit binary to 2 numbers
  return (int(bits[:sitty],2),int(bits[sitty:],2))
def unpackVar(binstack): # turns the entire varstack into readable numbers
  outputData = []
  for i in binstack:
    R,G,B,A = [int(i[a:a+8],2) for a in range(0,32,8)]
    outputData.append((R,G,B,A))
  return outputData
def decode(varstack, inputData, pointer): # decodes instructions 00 and 01, usefull
  instr = inputData[pointer:pointer+2]
  pointer+= 2
  if instr == "00": # 00, variable loading
    instr = inputData[pointer:pointer+1]
    pointer+= 1
    if instr == "0":
      outputData = (varstack[int(inputData[pointer:pointer+4],2)]) # 4 bit variable loading
      pointer+= 4
    elif instr == "1":
      outputData = (varstack[int(inputData[pointer:pointer+8],2)]) # 8 bit variable loading
      pointer+= 8
  elif instr == "01":
    instr = inputData[pointer:pointer+2]
    pointer+= 2
    if instr == "00":
      outputData = ((0,0,0,0)) # blank color
    elif instr == "01":
      instr = inputData[pointer:pointer+8] # monochrome color
      pointer+= 8
      mono = int(instr,2)
      outputData = ((mono,mono,mono,255))
    elif instr == "10": # 24 bit color
      instr = inputData[pointer:pointer+24]
      pointer+= 24
      R, G, B = [int(instr[i:i+8],2) for i in range(0,24,8)]
      outputData = (R, G, B, 255)
    elif instr == "11": # 32 bit color
      instr = inputData[pointer:pointer+32]
      pointer+= 32
      R, G, B, A = [int(instr[i:i+8],2) for i in range(0,32,8)]
      outputData = (R, G, B, A)
  else:
    return (pointer, False, instr)
  return (pointer, True, outputData)
def decoderecurse(inputData, pointer,instr10): # decodes the recurse function
  instr = inputData[pointer:pointer+2]
  pointer+= 2
  if instr == "00":
    instr = inputData[pointer:pointer+instr10[0]]
    pointer+= instr10[0]
    return (int(instr,2), pointer)
  elif instr == "01":
    instr = inputData[pointer:pointer+instr10[1]]
    pointer+=instr10[1]
    return (int(instr,2), pointer)
  elif instr == "10":
    instr = inputData[pointer:pointer+instr10[2]]
    pointer+= instr10[2]
    return (int(instr,2), pointer)
  elif instr == "11":
    instr = inputData[pointer:pointer+1]
    pointer+=1
    if instr == "0":
      instr = inputData[pointer:pointer+instr10[3]]
      pointer+= instr10[3]
      return (int(instr,2), pointer)
    elif instr == "1":
      instr = inputData[pointer:pointer+instr10[4]]
      pointer+= instr10[4]
      return (int(instr,2), pointer)
      
# ############################
# DECODER START

def LCIFdecode(file):
  txt = open(file,"rb")
  binD = txt.read(8)
  if binD == b"LCIF0002":
    print(f"\ndecoding {file}")
    print("Confirmed correct filetype")
    txt.seek(0)
    binD = txt.read()
    txt.close()  
      
    inputData = fromfile(binD) # unpacks to bytedata
    print("Converted to bytes")
    pointer = 64
    mms = inputData[pointer:pointer+8] # pulls metameta stack
    pointer+=8
    slice = mms[0] # slice pattern
    ressize = int(mms[2:8],2)
    if mms[1] == "0": # varstack size
      varstackSize = int(inputData[pointer:pointer+8],2)
      pointer+=8
    else:
      varstackSize = 256
    instruct10 = inputData[pointer:pointer+40]
    pointer+=40
    instruct10 = [int(instruct10[i:i+8],2) for i in range(0,40,8)]
    binresdata = inputData[pointer:pointer+(ressize*2)]
    pointer+=(ressize*2)
    resolution = unpackResolution(binresdata,ressize)
    # decodes the resolution
    outputData = []
  

    binstack = []
    for i in range(varstackSize): # reads the varstack
      binstack.append(inputData[pointer:pointer+32])
      pointer+=32
    varstack = unpackVar(binstack)
    print("loaded varstack")

    readingData = True
    while readingData: # this thing just does all the instruction reading, instr = instruction btw
      tryfor = decode(varstack,inputData,pointer)
      pointer = tryfor[0]
      if tryfor[1]:
        outputData.append(tryfor[2])
      else:
        instr = tryfor[2]
        if instr == "10":
          tryfor = decoderecurse(inputData,pointer,instruct10)
          pointer = tryfor[1]
          recurseColor = decode(varstack,inputData,pointer)
          pointer = recurseColor[0]
          if recurseColor[1]:
            for i in range(tryfor[0]):
              outputData.append(recurseColor[2])
          else:
            raise EOFError("file is not encoded properly")
        elif instr == "11":
          readingData = False
    print("Decoded to raw, encoding to png")
    print(f"expected: {resolution[0]*resolution[1]}\nactual: {len(outputData)}")
    image = Image.new("RGBA", (resolution[0], resolution[1]), "white")
    col = ImageDraw.Draw(image)
    if slice == "0":
      for y in range(resolution[1]+1):
        for x in range(resolution[0]+1):
         try:
          col.point([x,y], outputData[x+y*resolution[0]])
         except IndexError:
           pass
    else:
      for x in range(resolution[0]+1):
        for y in range(resolution[1]+1):
         try:
          col.point([x,y], outputData[y+x*resolution[1]])
         except IndexError:
           pass
    image.save(".".join(file.split(".")[:-1])+"(1).png")
    print("Finished")
  else:
    txt.close()
    print("0001")
    LCIF0001decode(file)

# SPVC slice pattern variable calculation
print("LCIF-0001-2 Decoder\nCreated By Alex Hall. November 3rd, 2019")
LCIFdecode(sys.argv[1])