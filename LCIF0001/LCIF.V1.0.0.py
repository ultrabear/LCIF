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

def mode256(inputList): # sorts the inputdata into a 256 variable stack, returns in a hex list 
  localCount = {}
  for i in inputList:
    if i in localCount:
      add = localCount[i]+1
      localCount[i] = (add)
    elif i != 0:
      localCount[i] = 1
  sort = sorted(localCount.items(), key=lambda s: s[1])
  finalSort = [a[0] for a in sort][::-1]
  varset = []
  if len(finalSort) >= 256:
    for i in range(256):
      varset.append(finalSort[i])
  else:
    for i in range(len(finalSort)):
      varset.append(finalSort[i])
    for i in range(256-len(finalSort)):
      varset.append(finalSort[-1])
  return varset
def boildownHex(inputList): # turns 6 hex values into 24 bit values for a list
  boildown = []
  for a in inputList:
    a = int(a, 16)
    a = str(bin(a)).split("b")[1]
    a = (24-len(a))*"0"+a
    boildown.append(a)
  return boildown
def xy(resolution): # turns the image resolution into a 64 bit string
  x = resolution[0]
  y = resolution[1]
  binX = str(bin(x)).split("b")[1]
  binX = (32-len(binX))*"0"+binX
  binY = str(bin(y)).split("b")[1]
  binY = (32-len(binY))*"0"+binY
  final = binX + binY
  return final
def binlen(num): #this does half of 10s work by counting the type of number needed
  binstr = str(bin(num)).split("b")[1]
  if len(binstr) < 8:
    binstr = (8-len(binstr))*"0"+binstr
    return "1000"+binstr
  elif len(binstr) < 16:
    binstr = (16-len(binstr))*"0"+binstr
    return "1001"+binstr
  elif len(binstr) < 32:
    binstr = (32-len(binstr))*"0"+binstr
    return "1010"+binstr
  elif len(binstr) < 64:
    binstr = (64-len(binstr))*"0"+binstr
    return "10110"+binstr
  elif len(binstr) < 128:
    binstr = (128-len(binstr))*"0"+binstr
    return "10111"+binstr
  else:
    raise OverflowError("a color repeats more than 2^128 times, twin counters are not supported in this encoder, also the resolution should have overflowed by now")
def colorInstruction(color, hexPalette): # deals with 00 and 01 instrcutions and returns a completed object
  endData = ""
  if color in hexPalette: # deals with variables
    endData+="00"
    variable = str(bin(hexPalette.index(color))).split("b")[1]
    if color in hexPalette[0:16]:
      variable = str(bin(hexPalette[0:16].index(color))).split("b")[1]
      variable = (4-len(variable))*"0"+variable
      endData+="0"+variable
    else:
      variable = (8-len(variable))*"0"+variable
      endData+="1"+variable
  else: # deals with reg colors, ranges from 8 bit to 24 bit
    endData+="01" 
    if color == 0:
      endData+="00"
    elif color[0:2] == color[2:4] and color[4:6] == color[2:4]: # 8 bit monochrome
      endData+="01"
      variable = str(bin(int(color[0:2],16))).split("b")[1]
      variable = (8-len(variable))*"0"+variable
      endData+=variable
    elif color[0] == color[1] and color[2] == color[3] and color[4] == color[5]: # 12 bit compress
      endData+="10"
      color12 = color[1]+color[3]+color[5]
      variable = str(bin(int(color12,16))).split("b")[1]
      variable = (12-len(variable))*"0"+variable
      endData+=variable
    else: # 24 bit full color
      endData+="11"
      RGB = "".join([(8-len(str(bin(int(color[i:i+2],16))).split("b")[1]))*"0"+str(bin(int(color[i:i+2],16))).split("b")[1] for i in range(0,6,2)])
      endData+= RGB
  return endData

# functions for the decoder


def unpackResolution(bits): # unpacks the resolution from 64 bit binary to 2 numbers
  return (int(bits[0:32],2),int(bits[32:64],2))
def unpackVar(binstack): # turns the entire varstack into readable numbers
  outputData = []
  for i in binstack:
    tup = str(hex(int(i,2))).split("x")[1]
    tup = (6-len(tup))*"0"+tup
    r = int(tup[0:2],16); g = int(tup[2:4],16); b = int(tup[4:6],16)
    outputData.append((r,g,b,255))
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
def decoderecurse(inputData, pointer): # decodes the recurse function
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
def statprint(completed, total): # its a percentage meter go V3
  percent = math.floor((completed/total)*1000)
  out = f"[{'#'*(math.floor(percent/100))}{(1-math.floor(percent/1000))*str(math.floor(percent/10)%10)}{'-'*(10-math.floor(percent/100)-1)}].{str(percent)[-1]}"
  return out

def read1(data):
    while True:
      out = data.read(8388608)
      if not(out):
        break
      yield out
  
# #######################################
# ENCODER START

def LCIFencode(file):
  print(f"\nencoding {file}")
  img = Image.open(file)
  colors = img.load()
  resolution = img.size # image resolution, would be (x,y)
  inputData = []
  for y in range(resolution[1]):
    for x in range(resolution[0]):
      tup = colors[x,y]
      color = ""
      try:
        if tup[3] == 0:
          color = 0
        else:
          for i in range(3):
            color+= (2-len(str(hex(tup[i])).split("x")[1]))*"0"+str(hex(tup[i])).split("x")[1]
      except IndexError:
        color = ""
        for i in range(3):
          color+= (2-len(str(hex(tup[i])).split("x")[1]))*"0"+str(hex(tup[i])).split("x")[1]
      inputData.append(color) # this is the input data, it should be a list of 3 byte 6 chr hex strings that goes down the image, its gonna be long so make it a tuple
  outputData = "0100110001000011010010010100011000110000001100000011000000110001" # this is the output variable being defined
  print("completed preload, res: %s*%s" %resolution)
  # this area is for variable calculation and putting unique preload data into the output file, after this the instructions would be written in
  outputData += xy(resolution) # puts resolution in
  hexPalette = mode256(inputData) # calculates the variables
  outputData += "".join(boildownHex(hexPalette)) # turns the variables into binary; makes a string of the binary variables and adds variables to outputData
  print("completed variable calculation")
  # this is where it puts the instructions in
  i = 0
  print("pixelcount: %s" %(resolution[0]*resolution[1]))
  with open("LCIF","a+") as tempout:
    tempout.seek(0)
    tempout.write(outputData)
    del outputData
    while i <= len(inputData):
      if i%5000 == 0:
        sys.stdout.write(statprint(i,len(inputData))+"\r")
        sys.stdout.flush()
      try:
        if inputData[i] == inputData[i+1]:
          recurse = True
          recurseCount = 1
          color = inputData[i]
          try:
            while recurse:
              if inputData[i] == inputData[i+1]:
                recurseCount+= 1
                i+= 1
              else:
                recurse = False
                dat = binlen(recurseCount)+colorInstruction(color,hexPalette)# add in the color after the counter
                tempout.write(dat)
          except IndexError:
              dat = binlen(recurseCount)+colorInstruction(color,hexPalette)# add in the color after the counter
              tempout.write(dat)
        else:
          dat = colorInstruction(inputData[i],hexPalette)
          tempout.write(dat)
      except IndexError:
        tempout.write(colorInstruction(inputData[i-1],hexPalette))
      i+=1
    tempout.write("11")
    print("\ncompleted image processing\npacking to bits")
    del inputData
    timestamp = time()
    tempout.seek(0)
    with open(".".join(file.split(".")[:-1])+".lcif","wb") as txt:
      for i in read1(tempout):
        txt.write(tofile(i))
  os.remove("LCIF")
  print("packed to bits, took %s miliseconds" % ((int(round(10000*(float(time()) - float(timestamp)))))/10))
  print("saved to file")

# ############################
# DECODER START

def LCIFdecode(file):
  print(f"\ndecoding {file}")
  with open(file,"rb") as txt:
    binD = txt.read(8)
    if binD == b"LCIF0001":
      print("confirmed correct filetype")
      txt.seek(0)
      binD = txt.read()
    else:
      print("incorrect filetype, exiting")
      txt.close()
      exit()
  inputData = fromfile(binD) # unpacks to bytedata
  resolution = unpackResolution(inputData[64:128]) # decodes the resolution
  outputData = []
  print("converted to bytes")

  pointer = 128
  binstack = []
  while pointer != 128+(256*24): # reads the varstack
    binstack.append(inputData[pointer:pointer+24])
    pointer+=24
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
        tryfor = decoderecurse(inputData,pointer)
        pointer = tryfor[1]
        recurseColor = decode(varstack,inputData,pointer)
        pointer = recurseColor[0]
        if recurseColor[1]:
          for i in range(tryfor[0]):
            outputData.append(recurseColor[2])
        else:
          print("oh shit")
      elif instr == "11":
        readingData = False
  print("decoded to raw, encoding to png")
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
  print("finished")

print("PNG <-> LCIF-0001 Converter Tool V1.0.0\nCreated By Alex Hall. October 19th, 2019")
if len(sys.argv) <= 1:
  ask = input("encode or decode: ")
  file = input("filename: ")
  if ask in ["e","en","encode"]:
    LCIFencode(file)
  elif ask in ["d","de","decode"]:
    LCIFdecode(file)
else:
  for i, a in enumerate(sys.argv):
    if a in ["-e","--encode"]:
      LCIFencode(sys.argv[i+1])
    if a in ["-d","--decode"]:
      LCIFdecode(sys.argv[i+1])
  print("\ncompleted all tasks")
input()