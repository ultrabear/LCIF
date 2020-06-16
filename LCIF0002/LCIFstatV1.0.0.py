#  Copyright (c) 2020, Alex Hall
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

# a program that gives statistics like resolution of an lcif file without fully opening it, saves potential zip bomb style image attacks

def bytetonum(indata):
  b = "".join([(8-len(bin(i).split("b")[1]))*"0"+bin(i).split("b")[1] for i in indata])
  return int(b, 2)

def scrape0001(file):
  x = bytetonum(file.read(4))
  y = bytetonum(file.read(4))
  print(f"Ver: 0001\nRes: {x} x {y}")

def scrape0002(file): # hell its hell thats what
  metameta = bin(file.read(1)[0]).split("b")[1]
  metameta = (8-len(metameta))*"0"+metameta
  slice = ["Horizontal","Vertical"][int(metameta[0])]
  if metameta[1] == "1":
    varstack = 256
  else:
    varstack = int(file.read(1)[0])
  reschunk = int(metameta[2:],2)
  repeatdata = [file.read(1)[0] for i in range(5)]
  dataneeded = int(((8-(reschunk*2%8))+reschunk*2)/8)
  trimmedres = ""
  for i in range(dataneeded):
    pre = bin(file.read(1)[0]).split("b")[1]
    trimmedres += (8-len(pre))*"0"+pre
  trimmedres = trimmedres[:reschunk*2]
  x = int(trimmedres[:reschunk],2)
  y = int(trimmedres[reschunk:],2) 
  print(f"Ver: 0002\nSlice: {slice}\nVarstack Size: {varstack}\nRepeat Chunk Size Map: {repeatdata}\nRes: {x} x {y}")
  
def versioncheck(file):
  token = file.read(8)
  if token == b"LCIF0002":
    return [True, 2]
  elif token == b"LCIF0001":
    return [True, 1]
  else:
    return [False]

def run(filename):
  print(filename)
  datafile = open(filename, "rb")
  usable = versioncheck(datafile)
  if usable[0]:
    if usable[1] == 1:
      scrape0001(datafile)
    elif usable[1] == 2:
      scrape0002(datafile)
  else:
    print("INCORRECT FILETYPE")  
  print("")
  
import sys
print(f"LCIF STAT V1.0.0 'AntiBomb'\nCreated By Alex Hall. April 2nd, 2020\n")
if len(sys.argv) > 1:
  for i in sys.argv[1:]:
    run(i)
else:
  i = input("which file to scan: ")
  run(i)