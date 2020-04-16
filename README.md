# LCIF file format

welcome to the front page of the LCIF project (Lossless Compressed Image Format), this is a file format developed over 8 months (0001 and 0002) based on linear image compression

# The Theory

LCIF compression is a linear compression algorithm that uses 2 main compression methods, repeated color compression and common color variable compression.  
Common Color Variable Compression takes common colors in the image and sorts them into a list at the start as variables callable by 8 bits instead of 24 or 32 bits for RGB and RGBA pixels.  
Repeated Color Compression notices when a color is repeated more than one time and writes that color once and attaches a number to represent the amount of times to repeat it.  

# Versions

### 10X (0001) Series
- 100
  - the original version, completely ram based and uses CCVC variable compressing
- 101
  - improvements were made to speed
- 102
  - introduction of SPVC variable calculation method
  - introduction of RRAW intermediary format
  - uses ramdisk, saves memory
- 103
  - QOL improvements with information displays
- 104
  - instead of going from png to raw to RRAW to LCIF, it now goes directly from png to RRAW, speeding up decoding
- 105
  - introduced faster binary decoder for RRAW data
### 11X (0002 w/ 0001 Decoder) Series
- 110
  - introduction of LCIF 0002 standard, can decode 0001 and 0002 and encodes 0002
- 111
  - QOL improvements
- 112
  - QOL improvements
- 113
  - disabled limiter on PIL max pixels
- 114
  - moved to faster binlen calculation function, increases compression
- 115
  - introduced faster binary decoder for RRAW data
  - introduced Bit By Bit (B3) decoder that stream decodes 0002, 0001 decoder not changed

# CHANGELOG

### UPDATE 2020-04-26
- updated 0003 specification file, it is still nowhere near complete but now some groundwork has been laid down

### UPDATE 2020-04-10
- updated README.md
- found V100 lying in the dustbin, its not not much

### UPDATE 2020-04-09
- added V1.0.5 encoder, uses a faster binary decoder for RRAW data and improved ram usage on encoding
- added V1.1.5 encoder and decoder, uses a much faster encoder and a slower but vastly more ram efficient decoder

### UPDATE 2020-04-03
- added V1.1.4, uses a better repeat binlen calculation function, also improved encoder ram usage
- minor tweaks to changelog
- added section "The Theory" to explain the idea behind LCIF compression
- edited 0002 specification file to make it make more sense

### UPDATE 2020-04-02
- added V1.1.3, moves limiter on PIL image size to maximum limits of LCIF ((2^64-1)x(2^64-1))
- added first draft of LCIF-0003 file format specification
- improved layout of changelog

### UPDATE 2020-01-24
- added V1.1.1 0002 encoder and V1.1.2 0002 encoder
