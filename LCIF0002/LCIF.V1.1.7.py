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
import math, sys, os, multiprocessing, glob, statistics
from time import time
CpuCoreCount = multiprocessing.cpu_count()
Image.MAX_IMAGE_PIXELS = 85070591730234615847396907784232501249 # exactly (2^63-1)^2
if sys.version_info[0] < 3 or sys.version_info[1] < 8 and not("-s" in sys.argv):
  print("WARN: not using latest version of Python\n Consider using latest version for increased performance")

def decodebinnumber(inData): #decodes any large bytes obj into an int
  return int.from_bytes(inData, "big")
def read20gen(data,sRRAWV):
  while True:
    out = data.read(sRRAWV+4)
    if not(out):
      break
    yield out
def mode256(inputList,leninput,sRRAWV): # sorts the inputdata into a 256 variable stack UPDATE 115 also does Binlen calculation
  localCountV = {}
  localCount = {}
  prog = 0
  for a in read20gen(inputList,sRRAWV):
    if prog%1024 == 0:
      sys.stdout.write(f"Pass 1 : {statprint(prog,leninput)}{' '*7}\r")
      sys.stdout.flush()
    prog+=1
    i = bytes(a[sRRAWV:])
    localCount[decodebinnumber(a[:sRRAWV])] = 0
    if i in localCountV:
      localCountV[i] = (localCountV[i]+1) #adds one to counter
    elif i[3] != 0:
      localCountV[i] = 1
  finalSortV = [a[0] for a in sorted(localCountV.items(), key=lambda s: s[1])][::-1]
  if len(finalSortV) >= 256:
      varset = [finalSortV[i] for i in range(256)]
  else:
    varset = finalSortV # if there are less than 256 colors it counts under
  # so at this point it has a list of the repeat counts
  binlens = sorted(list(dict.fromkeys([len(bin(i))-2 for i in list(localCount) if i != 1]))) # so now it just has every binlen used
  if len(binlens) == 0:
    Blen = [0,0,0,0,0]
  elif len(binlens) == 5:
    Blen = binlens
  elif len(binlens) <= 5:
    Blen = [binlens[0],binlens[0]+1,round(statistics.mean([binlens[0],binlens[-1]])),binlens[-1]-1,binlens[-1]]
  else:
    Blen = [binlens[0],binlens[1],round(statistics.mean([binlens[1],binlens[-2]])),binlens[-2],binlens[-1]]
  return (varset,len(varset),Blen)
def boildownHex(inputList): # turns 32b values into 32 bit values for a list
  boildown = []
  data = ""
  for a in inputList:
    for i in a:
      data+= (8-(len(bin(i))-2))*"0"+(bin(i)).split("b")[1]
  return data
def returnres(resolution): # turns the image resolution into a X bit string
  x = resolution[0]
  y = resolution[1]
  binX = (bin(x)).split("b")[1]
  binY = (bin(y)).split("b")[1]
  if len(binX) > len(binY):
    width = len(binX)
  else:
    width = len(binY)
  binX = (width-len(binX))*"0"+binX
  binY = (width-len(binY))*"0"+binY
  final = binX + binY
  return [final,width]
def binlen(num,lens): #this does half of 10s work by calculating the type of number needed
  bins = (bin(num)).split("b")[1]
  if len(bins) <= lens[0]:
    bins = (lens[0]-len(bins))*"0"+bins
    return "1000"+bins
  elif len(bins) <= lens[1]:
    bins = (lens[1]-len(bins))*"0"+bins
    return "1001"+bins
  elif len(bins) <= lens[2]:
    bins = (lens[2]-len(bins))*"0"+bins
    return "1010"+bins
  elif len(bins) <= lens[3]:
    bins = (lens[3]-len(bins))*"0"+bins
    return "10110"+bins
  elif len(bins) <= lens[4]:
    bins = (lens[4]-len(bins))*"0"+bins
    return "10111"+bins
  else:
    print(bins)
    print(lens)
    raise OverflowError("a color repeats more than theoretically_supported times, twin counters are not supported in this encoder, also the resolution should have overflowed by now, something has been deeply broken to get this error message")
def colorInstruction(incolor, hexPalette): # deals with 00 and 01 instructions and returns a completed object
  endData = ""
  A = incolor[3]
  RGB = incolor[0:3]
  if incolor in hexPalette: # deals with variables
    endData+="00"
    variable = (bin(hexPalette.index(incolor))).split("b")[1]
    if incolor in hexPalette[0:16]:
      variable = (bin(hexPalette[0:16].index(incolor))).split("b")[1]
      variable = (4-len(variable))*"0"+variable
      endData+="0"+variable
    else:
      variable = (8-len(variable))*"0"+variable
      endData+="1"+variable
  else: # deals with reg colors, ranges from 8 bit to 24 bit
    endData+="01"
    if A == 0:
       endData+="00"
    elif RGB[0] == RGB[1] and RGB[1] == RGB[2] and A == 255: # 8 bit monochrome
      endData+="01"
      variable = (bin(RGB[0])).split("b")[1]
      variable = (8-len(variable))*"0"+variable
      endData+=variable
    elif A == 255: # 24 bit color
      endData+="10"
      out = "".join([(10-len(bin(RGB[i])))*"0"+(bin(RGB[i])).split("b")[1] for i in range(3)]) # 10 instead of 8 to account for 0b
      endData+= out
    else: # 32 bit full color
      endData+="11"
      out = "".join([(10-len(bin(incolor[i])))*"0"+(bin(incolor[i])).split("b")[1] for i in range(4)])
      endData+= out
  return endData

# functions for the decoder


def unpackResolution(bits,sitty): # unpacks the resolution from X bit binary to 2 numbers
  return (int(bits[:sitty],2),int(bits[sitty:],2))
def unpackVar(binstack): # turns the entire varstack into readable colors
  outputData = []
  for i in binstack:
    R,G,B,A = [int(i[a:a+8],2) for a in range(0,32,8)]
    outputData.append((R,G,B,A))
  return outputData
def decode(varstack, inD, pointer): # decodes instructions 00 and 01, usefull
  instr = inputDataReturn(inD,2)
  if instr == "00": # 00, variable loading
    instr = inputDataReturn(inD,1)
    if instr == "0":
      outputData = (varstack[int(inputDataReturn(inD,4),2)]) # 4 bit variable loading
    elif instr == "1":
      outputData = (varstack[int(inputDataReturn(inD,8),2)]) # 8 bit variable loading
  elif instr == "01":
    instr = inputDataReturn(inD,2)
    if instr == "00":
      outputData = ((0,0,0,0)) # blank color
    elif instr == "01":
      instr = inputDataReturn(inD,8) # monochrome color
      mono = int(instr,2)
      outputData = ((mono,mono,mono,255))
    elif instr == "10": # 24 bit color
      instr = inputDataReturn(inD,24)
      R, G, B = [int(instr[i:i+8],2) for i in range(0,24,8)]
      outputData = (R, G, B, 255)
    elif instr == "11": # 32 bit color
      instr = inputDataReturn(inD,32)
      R, G, B, A = [int(instr[i:i+8],2) for i in range(0,32,8)]
      outputData = (R, G, B, A)
  else:
    return (pointer, False, instr)
  return (pointer, True, outputData)
def decoderecurse(inD, pointer,instr10): # decodes the recurse function
  instr = inputDataReturn(inD,2)
  if instr == "00":
    instr = inputDataReturn(inD,instr10[0])
    return (int(instr,2), pointer)
  elif instr == "01":
    instr = inputDataReturn(inD,instr10[1])
    return (int(instr,2), pointer)
  elif instr == "10":
    instr = inputDataReturn(inD,instr10[2])
    return (int(instr,2), pointer)
  elif instr == "11":
    instr = inputDataReturn(inD,1)
    if instr == "0":
      instr = inputDataReturn(inD,instr10[3])
      return (int(instr,2), pointer)
    elif instr == "1":
      instr = inputDataReturn(inD,instr10[4])
      return (int(instr,2), pointer)

 # byte depacker V4
def unpack(bits):
  dat = (bin(bits)).split("b")[1]
  return ((8-len(dat))*"0")+dat

def fromfile(byte): # unpacks bits into string of 1 and 0
  return "".join([unpack(i) for i in byte])

def statprint(completed, total):
  if completed > total:
    total = completed
  percent = math.floor((completed/total)*1000)
  out = f"[{'#'*(math.floor(percent/100))}{(1-math.floor(percent/1000))*str(math.floor(percent/10)%10)}{'-'*(10-math.floor(percent/100)-1)}].{str(percent)[-1]}"
  return out

# some encoder stuffs
def directBinNumber(inData,length):
  return tuple([(inData >> (8*i) & 0xff ) for i in range(length)][::-1])

def directbinstr(data,length):
  data = (bin(data)).split("b")[1]
  return (length-len(data))*"0"+data

def rawgeneratorhz(img,resolution):
  for y in range(resolution[1]):
    for x in range(resolution[0]):
      tup = img.load()[x,y]
      yield (bytes(tup)) # this is the input data

def rawgeneratorvt(img,resolution):
  for x in range(resolution[0]):
    for y in range(resolution[1]):
      tup = img.load()[x,y]
      yield (bytes(tup)) # this is the input data

def rrawgenerator(inputData): # lookahead based encoder to compress repetent colors, twice as fast as of V116 :) RRAW20 encoder
    gen, file, res, sRRAWV = inputData
    i = 0
    size = 0
    length = res[0]*res[1]
    currentColor = next(gen)
    recurse = 0
    while i <= length:
      if i%15000 == 0:
        sys.stdout.write(f"Decoding to RRAW{sRRAWV}:4 {statprint(i,length)}\r")
        sys.stdout.flush()
      try:
        color = currentColor
        currentColor = next(gen)
        if recurse > 0:
          if color == currentColor:
            recurse+=1
          else:
            file.write(bytes(directBinNumber(recurse,sRRAWV))+color)
            size+=1
            recurse = 0
        elif color == currentColor:
          recurse = 2
        else:
          file.write(bytes(directBinNumber(1,sRRAWV))+color)
          size+=1
      except StopIteration:
        if recurse > 0:
          file.write(bytes(directBinNumber(recurse,sRRAWV))+color)
          size+=1
        else:
          file.write(bytes(directBinNumber(1,sRRAWV))+color)
          size+=1
        i+=1
      i+=1
    return size

def RRAW20toLCIF0002(colorobj):
    currentColor, binlens, hexPalette, sRRAWV = colorobj
    count = decodebinnumber(currentColor[:sRRAWV])
    color = bytes(currentColor[sRRAWV:])
    if count != 1:
      return (binlen(count,binlens)+colorInstruction(color,hexPalette[0]))
    else:
      return (colorInstruction(color,hexPalette[0]))

class BinaryBytes:
  def __init__(self, fileobj):
    self.fileobj = open(fileobj, "wb")
    self.ram = ""

  def write(self, bindata):
    self.ram += bindata
    if len(self.ram) >= 8:
      writed = [int(self.ram[i:i+8],2) for i in range(0,len(self.ram)-len(self.ram)%8,8)]
      self.ram = self.ram[len(self.ram)-len(self.ram)%8:]
      self.fileobj.write(bytes(writed))

  def finalize(self, bindata):
    self.ram += bindata
    self.ram += "".join(["1" for i in range(8-len(self.ram)%8)])
    writed = [int(self.ram[i:i+8],2) for i in range(0,len(self.ram)-len(self.ram)%8,8)]
    self.ram = ""
    self.fileobj.write(bytes(writed))
  
  def close(self):
    self.fileobj.close()

# ###################################
# ENCODER START
def LCIF0002encode(file):
    print(f"\nencoding {file}")
    print("Loading Image & Clearing Stack")
    img = Image.open(file).convert("RGBA")
    resolution = img.size # image resolution, would be (x,y)
    files = glob.glob("**/*", recursive=True) # takes out trash
    sRRAWV = math.ceil((len(bin(resolution[0]*resolution[1]))-2)/8)
    for i in ["RRAW0","RRAW1"]:
      if i in files:
        os.remove(i) # garbage collection end
    RRAW0 = open("RRAW0","ab+") # horizonatal
    RRAW1 = open("RRAW1","ab+") # vertical
    with ThreadPool(2) as pool:
      R0, R1 = pool.map(rrawgenerator, [[rawgeneratorhz(img,resolution),RRAW0,resolution,sRRAWV], [rawgeneratorvt(img,resolution),RRAW1,resolution,sRRAWV]])
    img.close() # closes image
    print(f"Decoding to RRAW{sRRAWV}:4 COMPLETE{' '*10}")
    RRAW0.seek(0)
    RRAW1.seek(0)
    if R0 > R1: # this block decides whether to use horizontal or vertical
      RRAW = RRAW1
      RRAW0.close()
      os.remove("RRAW0")
      stack = "1" # stack is the metameta stack
      Rlen = R1 # defines len for pass 1 encode
    else:
      RRAW = RRAW0
      RRAW1.close()
      os.remove("RRAW1")
      stack = "0" # defines how its encoded, 0 is horizontal
      Rlen = R0
    RRAW.seek(0)
    hexPalette = mode256(RRAW,Rlen,sRRAWV) # calculates the variables, rewritten so many times and now supports RGBA, bulk of pass1
    if hexPalette[1] != 256:
      stack+="0"
      stack16 = directbinstr(hexPalette[1],8)
    else:
      stack+="1"
      stack16 = ""
    # end raw
    outputData = "0100110001000011010010010100011000110000001100000011000000110010" # this is the output variable being defined, it also writes LCIF0002
    # this area is for putting pass1 data into the output file
    resdata = returnres(resolution) # calculate res
    outputData += stack+directbinstr(resdata[1],6)+stack16 # finalizes the metametastack, if stack[1] == 1 then stack16 should be blank
    #definer for 5 bytes of 10 instr
    binlens = hexPalette[2]
    outputData+= "".join([directbinstr(i,8) for i in binlens])
    outputData += resdata[0] # adds in resolution
    outputData += boildownHex(hexPalette[0]) # turns the variables into binary; makes a string of the binary variables and adds variables to outputData
    # where it puts the instructions in

    i = 0
    RRAW.seek(0)
    print(f"\rPass 1 COMPLETE{' '*12}\n Varcount: {len(hexPalette[0])}\n Encode Path: {(stack[0])}\n Resolution: {resolution[0]}*{resolution[1]}\n Pixelcount: {resolution[0]*resolution[1]}")
    del files; del resdata
    tempout = BinaryBytes(".".join(file.split(".")[:-1])+".lcif")
    tempout.write(outputData)
    del outputData
    readingData = True
    with ThreadPool(CpuCoreCount) as pool:
      while readingData:
        if i%5000 == 0:
          sys.stdout.write(f"Converting to LCIF {statprint(i,Rlen)}\r")
          sys.stdout.flush()
        currentColor = []
        for a in range(50000):
          i += 1
          b = RRAW.read(sRRAWV+4)
          if b:
            currentColor.append([b, binlens, hexPalette, sRRAWV])
        if currentColor:
          tempout.write("".join(pool.map(RRAW20toLCIF0002, currentColor)))
        else:
          tempout.finalize("11")
          readingData = False
    tempout.close()
    RRAW.close()
    try:
      os.remove("RRAW0")
    except:
      os.remove("RRAW1")
    sys.stdout.write(f"Converting to LCIF COMPLETE{' '*10}")
    sys.stdout.flush()
    with open(".".join(file.split(".")[:-1])+".lcif","rb") as txt:
      finalsize = len(txt.read())
    print(f"\nRatios:\n RGB  : {round((resolution[0]*resolution[1]*3/finalsize)*10)/10}:1 \n RGBA : {round((resolution[0]*resolution[1]*4/finalsize)*10)/10}:1")

# ############################
# DECODER START

GinputDataPos = 0
GinputDataRAM = []
GinputDataRAMpos = 0
def inputDataReturn(fileOBJ, amount): # B3 return function
  global GinputDataPos; global GinputDataRAM; global GinputDataRAMpos
  del GinputDataRAM[:GinputDataRAMpos]
  GinputDataRAMpos = amount
  if len(GinputDataRAM) < amount:
    amntread = 1024
    GinputDataRAM += [i for i in fromfile(fileOBJ.read(amntread))]
    GinputDataPos += amntread
    return "".join(GinputDataRAM[:amount])
  else:
    return "".join(GinputDataRAM[:amount])


def LCIF0002decode(file):
  global GinputDataPos; global GinputDataRAM; global GinputDataRAMpos
  GinputDataPos = 0
  GinputDataRAM = []
  GinputDataRAMpos = 0
  print(f"\ndecoding {file}")
  LCIFobj = open(file,"rb")
  binD = LCIFobj.read(8)
  if binD == b"LCIF0002":
    print("Confirmed correct filetype")
    LCIFobj.seek(0)
    LCIFlen = len(LCIFobj.read())
    LCIFobj.seek(0)
    a = inputDataReturn(LCIFobj,64) # unpacks to bytedata
    mms = inputDataReturn(LCIFobj,8) # pulls metameta stack
    slice = mms[0] # slice pattern
    ressize = int(mms[2:8],2)
    if mms[1] == "0": # varstack size
      varstackSize = int(inputDataReturn(LCIFobj,8),2)
    else:
      varstackSize = 256
    instruct10 = inputDataReturn(LCIFobj,40)
    instruct10 = [int(instruct10[i:i+8],2) for i in range(0,40,8)]
    binresdata = inputDataReturn(LCIFobj,ressize*2)
    resolution = unpackResolution(binresdata,ressize)
    # decodes the resolution
    outputData = []


    binstack = []
    for i in range(varstackSize): # reads the varstack
      binstack.append(inputDataReturn(LCIFobj,32))
    varstack = unpackVar(binstack)
    print("loaded varstack\nDecoding to RAW")
    pointer = 0
    readingData = True
    while readingData: # this thing just does all the instruction reading, instr = instruction btw
      if len(outputData)%5000 == 0:
        sys.stdout.write("\r"+statprint(GinputDataPos,LCIFlen))
        sys.stdout.flush()
      tryfor = decode(varstack,LCIFobj,pointer)
      pointer = tryfor[0]
      if tryfor[1]:
        outputData.append(tryfor[2])
      else:
        instr = tryfor[2]
        if instr == "10":
          tryfor = decoderecurse(LCIFobj,pointer,instruct10)
          pointer = tryfor[1]
          recurseColor = decode(varstack,LCIFobj,pointer)
          pointer = recurseColor[0]
          if recurseColor[1]:
            for i in range(tryfor[0]):
              outputData.append(recurseColor[2])
          else:
            raise EOFError("file is not encoded properly")
        elif instr == "11":
          readingData = False
    LCIFobj.close()
    print("\nDecoded to raw, encoding to png")
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
    LCIFobj.close()
    print("Incorrect filetype/version, trying 0001")
    LCIF0001decode(file)

################### LCIF0001 decoding #####################################################

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

# #######################
# 0001 DECODER START

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

def prettyprint(indict):
  maxln = 0
  minln = 0
  for i in indict.keys():
    if len(i) > maxln:
      maxln = len(i)
    if len(indict[i]) > minln:
      minln = len(indict[i])
  for i in indict.keys():
    print(f"{i}{(maxln-len(i))*' '} : {(minln-len(indict[i]))*' '}{indict[i]}")

VerConfig = {"DE1":"RAM:1.0.0:N", "DE2":"B3:1.1.5:N", "EN2":"2P:1.1.7:N", "RRAW4V":"VLA:1.1.7:N"} # n is normal s is statistic r is rgb instr map
print("PNG <-> LCIF-0002 Converter Tool V1.1.7 'ThreadRipper'\nCreated By Alex Hall. July 25th, 2020")
if len(sys.argv) <= 1:
  ask = input("encode or decode: ")
  file = input("filename: ")
  if ask in ["e","en","encode"]:
    LCIF0002encode(file)
  elif ask in ["d","de","decode"]:
    LCIF0002decode(file)
  input()
else:
  for i, a in enumerate(sys.argv):
    if a in ["-c","--config"]:
      print(f"\nVerConfig:\nThreads: {CpuCoreCount}")
      prettyprint(VerConfig)
    if a in ["-e","--encode"]:
      LCIF0002encode(sys.argv[i+1])
    if a in ["-d","--decode"]:
      LCIF0002decode(sys.argv[i+1])
  print("\ncompleted all tasks")