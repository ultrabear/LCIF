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
CpuCoreCount = multiprocessing.cpu_count()
Image.MAX_IMAGE_PIXELS = 85070591730234615847396907784232501249 # exactly (2^63-1)^2

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
      inputDataReturn(inD,4)
      instrcounter["00:0"] = instrcounter["00:0"]+1
    elif instr == "1":
      inputDataReturn(inD,8)
      instrcounter["00:1"] = instrcounter["00:1"]+1
  elif instr == "01":
    instr = inputDataReturn(inD,2)
    if instr == "00":
      instrcounter["01:00"] = instrcounter["01:00"]+1
    elif instr == "01":
      inputDataReturn(inD,8) # monochrome color
      instrcounter["01:01"] = instrcounter["01:01"]+1
    elif instr == "10": # 24 bit color
      inputDataReturn(inD,24)
      instrcounter["01:10"] = instrcounter["01:10"]+1
    elif instr == "11": # 32 bit color
      inputDataReturn(inD,32)
      instrcounter["01:11"] = instrcounter["01:11"]+1
  else:
    return (pointer, False, instr)
  return (pointer, True, 0)
def decoderecurse(inD, pointer,instr10): # decodes the recurse function
  instr = inputDataReturn(inD,2)
  instrcounter["10"] = instrcounter["10"]+1
  if instr == "00":
    inputDataReturn(inD,instr10[0])
    return (0, pointer)
  elif instr == "01":
    inputDataReturn(inD,instr10[1])
    return (0, pointer)
  elif instr == "10":
    inputDataReturn(inD,instr10[2])
    return (0, pointer)
  elif instr == "11":
    instr = inputDataReturn(inD,1)
    if instr == "0":
      inputDataReturn(inD,instr10[3])
      return (0, pointer)
    elif instr == "1":
      inputDataReturn(inD,instr10[4])
      return (0, pointer)

 # byte packer and depacker V4
def pack(byte): # packs bytes of 1 and 0 into bits
  return int(byte, 2)
def unpack(bits):
  dat = (bin(bits)).split("b")[1]
  return ((8-len(dat))*"0")+dat

def fromfile(byte): # unpacks bits into string of 1 and 0
  return "".join([unpack(i) for i in byte])
def tofile(outputData): # takes the string of 1 and 0 and packs it into byte objects
  outputData = outputData+(((8-len(outputData))%8)*"1")
  outputData = [outputData[i*8:i*8+8] for i in range(int(len(outputData)/8))]
  with ThreadPool(CpuCoreCount) as pool:
    outputData = bytes(pool.map(pack, outputData))
  return outputData

def statprint(completed, total):
  percent = math.floor((completed/total)*1000)
  out = f"[{'#'*(math.floor(percent/100))}{(1-math.floor(percent/1000))*str(math.floor(percent/10)%10)}{'-'*(10-math.floor(percent/100)-1)}].{str(percent)[-1]}"
  return out

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
    amntread = 10240
    GinputDataRAM += [i for i in fromfile(fileOBJ.read(amntread))]
    GinputDataPos += amntread
    return "".join(GinputDataRAM[:amount])
  else:
    return "".join(GinputDataRAM[:amount])

def LCIFdecode(file):
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

    binstack = []
    for i in range(varstackSize): # reads the varstack
      binstack.append(inputDataReturn(LCIFobj,32))
    varstack = unpackVar(binstack)
    global instrcounter
    instrcounter = {"00:0":0, "00:1":0, "01:00":0, "01:01":0, "01:10":0, "01:11":0, "10":0}
    pointer = 0
    readingData = True
    while readingData: # this thing just does all the instruction reading, instr = instruction btw
      if pointer%5000 == 0:
        sys.stdout.write("\r"+statprint(GinputDataPos,LCIFlen))
        sys.stdout.flush()
      pointer+=1
      tryfor = decode(varstack,LCIFobj,pointer)
      pointer = tryfor[0]
      if tryfor[1]:
        pass
      else:
        instr = tryfor[2]
        if instr == "10":
          tryfor = decoderecurse(LCIFobj,pointer,instruct10)
          pointer = tryfor[1]
          recurseColor = decode(varstack,LCIFobj,pointer)
          pointer = recurseColor[0]
          if recurseColor[1]:
            pass
          else:
            raise EOFError("file is not encoded properly")
        elif instr == "11":
          readingData = False
    LCIFobj.close()
    print("")
    for i in instrcounter.keys():
      print(f"{i} : {instrcounter[i]}")
  else:
    LCIFobj.close()
    print("Incorrect filetype/version")

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

VerConfig = {"DE2":"B3:1.1.5:S"} # update every version, DE: n is normal s is statistic r is rgb instr map
print("PNG <-> LCIF-0002 Converter Tool B3:1.1.5:S 'quickstat'\nCreated By Alex Hall. June 16th, 2020")
if len(sys.argv) <= 1:
  ask = input("encode or decode: ")
  file = input("filename: ")
  if ask in ["d","de","decode"]:
    LCIFdecode(file)
  input()
else:
  for i, a in enumerate(sys.argv):
    if a in ["-c","--config"]:
      print("\nVerConfig:")
      prettyprint(VerConfig)
    if a in ["-d","--decode"]:
      LCIFdecode(sys.argv[i+1])
  print("\ncompleted all tasks")