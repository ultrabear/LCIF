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

def read20gen(data):
  while True:
    out = data.read(20)
    if not(out):
      break
    yield out
def mode256(inputList): # sorts the inputdata into a 256 variable stack, returns in a hex list 
  localCount = {}
  for a in read20gen(inputList):
    i = bytes(a[16:20])
    if i in localCount:
      localCount[i] = (localCount[i]+1) #adds one to counter
    elif i[3] != 0:
      localCount[i] = 1
  sort = sorted(localCount.items(), key=lambda s: s[1])
  finalSort = [a[0] for a in sort][::-1]
  varset = []
  if len(finalSort) >= 256:
    for i in range(256):
      varset.append(finalSort[i][0:3])
  else:
    for i in range(len(finalSort)): # if there are less than 256 colors this adds padding to the list, maybe i should add a definer byte in 0002 that says the amount of vars it picks up to save a bit more space
      varset.append(finalSort[i][0:3])
    for i in range(256-len(finalSort)):
      varset.append(finalSort[-1][0:3])
  return varset
def boildownHex(inputList): # turns 6 hex values into 24 bit values for a list
  boildown = []
  data = ""
  for a in inputList:
    for i in a:
      data+= (8-len(str(bin(i)).split("b")[1]))*"0"+str(bin(i)).split("b")[1]
  return data
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
def colorInstruction(incolor, hexPalette): # deals with 00 and 01 instrcutions and returns a completed object
  endData = ""
  A = incolor[3]
  RGB = incolor[0:3]
  if RGB in hexPalette and A != 0: # deals with variables
    endData+="00"
    variable = str(bin(hexPalette.index(RGB))).split("b")[1]
    if RGB in hexPalette[0:16]:
      variable = str(bin(hexPalette[0:16].index(RGB))).split("b")[1]
      variable = (4-len(variable))*"0"+variable
      endData+="0"+variable
    else:
      variable = (8-len(variable))*"0"+variable
      endData+="1"+variable
  else: # deals with reg colors, ranges from 8 bit to 24 bit
    endData+="01" 
    if A == 0:
      endData+="00"
    elif RGB[0] == RGB[1] and RGB[1] == RGB[2]: # 8 bit monochrome
      endData+="01"
      variable = str(bin(RGB[0])).split("b")[1]
      variable = (8-len(variable))*"0"+variable
      endData+=variable
    else:
      color = "".join([(2-len(str(hex(i)).split("x")[1]))*"0"+str(hex(i)).split("x")[1] for i in RGB])
      if color[0] == color[1] and color[2] == color[3] and color[4] == color[5]: # 12 bit compress
        endData+="10"
        color12 = color[1]+color[3]+color[5]
        variable = str(bin(int(color12,16))).split("b")[1]
        variable = (12-len(variable))*"0"+variable
        endData+=variable
      else: # 24 bit full color
        endData+="11"
        out = "".join([(8-len(str(bin(RGB[i])).split("b")[1]))*"0"+str(bin(RGB[i])).split("b")[1] for i in range(0,3)])
        endData+= out
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

def read1Tofile(data):
    while True:
      out = data.read(8388608)
      if not(out):
        break
      yield out
  
def directBinNumber(number):
  data = str(bin(number)).split("b")[1]
  data = (128-len(data))*"0"+data
  return tuple([int(data[i:i+8],2) for i in range(0,128,8)])

def decodebinnumber(inData):
  a = "".join([(8-len(str(bin(i)).split("b")[1]))*"0"+str(bin(i)).split("b")[1] for i in inData])
  return int(a,2)
# #######################################
# ENCODER START

def LCIFencode(file):
  with open("RRAW", "ab+") as RRAW:
    with open("RAW","ab+") as inputDataFile:
      inputDataFile.seek(0)
      print(f"\nencoding {file}")
      print("Decoding to RAW")
      img = Image.open(file)
      resolution = img.size # image resolution, would be (x,y)
      for y in range(resolution[1]):
        for x in range(resolution[0]):
          tup = img.load()[x,y]
          if len(tup) != 4:
            inputDataFile.write(bytes(tup+(255,)))
          else:
            inputDataFile.write(bytes(tup)) # this is the input data, its gonna be long
      inputDataFile.seek(0)
      i = 0
      length = resolution[0]*resolution[1]
      colorpointer = 0
      print("Converting RAW to RRAW")
      while i <= length:
        if i%5000 == 0:
          sys.stdout.write(statprint(i,length)+"\r")
          sys.stdout.flush()
        try:
          currentColor = inputDataFile.read(4)
          colorpointer+=4
          if currentColor:
            if currentColor == inputDataFile.read(4):
              inputDataFile.seek(colorpointer)
              recurse = True
              recurseCount = 1
              color = currentColor
              try:
                while recurse:
                  if color == inputDataFile.read(4): # adds up the recurse counter
                    recurseCount+= 1
                    i+= 1
                    colorpointer+=4
                  else:
                    recurse = False
                    # add in the color after the counter
                    RRAW.write(bytes(directBinNumber(recurseCount))+color)
                    inputDataFile.seek(colorpointer)                  
              except EOFError:
                  inputDataFile.seek(colorpointer)
                  RRAW.write(bytes(directBinNumber(recurseCount))+color)
            else:
              inputDataFile.seek(colorpointer)
              RRAW.write(bytes(directBinNumber(1))+currentColor)
        except EOFError:
          inputDataFile.seek(colorpointer)
          RRAW.write(bytes(directBinNumber(1))+currentColor)
        i+=1
    os.remove("RAW")
    # end raw
    outputData = "0100110001000011010010010100011000110000001100000011000000110001" # this is the output variable being defined, it also writes LCIF0001 in bytenary
    print("\nRes: %s*%s" %resolution)
    # this area is for variable calculation and putting unique preload data into the output file, after this the instructions would be written in
    outputData += xy(resolution) # puts resolution in
    RRAW.seek(0)
    hexPalette = mode256(RRAW) # calculates the variables, rewritten in V1.0.2 
    outputData += boildownHex(hexPalette) # turns the variables into binary; makes a string of the binary variables and adds variables to outputData
    # this is where it puts the instructions in
    i = 0
    RRAW.seek(0)
    print("Pixelcount: %s\nConverting to LCIF" %(resolution[0]*resolution[1]))
    colorpointer = 0
    with open("LCIF","a+") as tempout:
      tempout.seek(0)
      tempout.write(outputData)
      del outputData
      readingData = True
      while readingData:
        if i%5000 == 0:
          sys.stdout.write(statprint(i,length)+"\r")
          sys.stdout.flush()
        currentColor = RRAW.read(20)
        if currentColor:
          count = decodebinnumber(currentColor[0:16])
          color = bytes(currentColor[16:20])
          colorpointer+=20
          i += count
          if count != 1:
            tempout.write(binlen(count)+colorInstruction(color,hexPalette))
          else:
            tempout.write(colorInstruction(color,hexPalette))
        else:
          readingData = False
      tempout.write("11")
      print("\ncompleted image processing\npacking to bits")
      timestamp = time()
      tempout.seek(0)
      with open(".".join(file.split(".")[:-1])+".lcif","wb") as txt:
        for i in read1Tofile(tempout):
          txt.write(tofile(i))
  os.remove("RRAW")
  os.remove("LCIF")
  print("packed to bits, took %s miliseconds" % ((int(round(10000*(float(time()) - float(timestamp)))))/10))

# ############################
# DECODER START

def LCIFdecode(file):
  print(f"\ndecoding {file}")
  with open(file,"rb") as txt:
    binD = txt.read(8)
    if binD == b"LCIF0001":
      print("Confirmed correct filetype")
      txt.seek(0)
      binD = txt.read()
    else:
      print("Incorrect filetype, exiting")
      txt.close()
      exit()
  inputData = fromfile(binD) # unpacks to bytedata
  resolution = unpackResolution(inputData[64:128]) # decodes the resolution
  outputData = []
  print("Converted to bytes")

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
          raise EOFError("file is not encoded properly")
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

# SPVC slice pattern variable calculation
print("PNG <-> LCIF-0001 Converter Tool V1.0.3 'InfoBox'\nCreated By Alex Hall. October 26th, 2019")
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