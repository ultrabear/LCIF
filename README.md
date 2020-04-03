# LCIF file format

welcome to the front page of the LCIF project, this is a file format i have developed over 8 months and am finally putting on github for public use, its strength lies in low color images, where the 0002 standard is getting ever closer to beating the compression of PNG

# The Theory

LCIF compression is a linear compression algorithm that uses 2 main compression methods, repeated color compression and common color variable compression.  
Common Color Variable Compression takes common colors in the image and sorts them into a list at the start as variables callable by 8 bits instead of 24 or 32 bits for RGB and RGBA pixels.  
Repeated Color Compression notices when a color is repeated more than one time and writes that color once and attaches a number to represent the amount of times to repeat it.  

# CHANGELOG

### UPDATE 2020-04-03
- added V1.1.4, uses a better repeat binlen calculation function, also improved encoder ram usage
- minor tweaks to changelog
- added section "The Theory" to explain the idea behind LCIF compression

### UPDATE 2020-04-02
- added V1.1.3, moves limiter on PIL image size to maximum limits of LCIF ((2^64-1)x(2^64-1))
- added first draft of LCIF-0003 file format specification
- improved layout of changelog

### UPDATE 2020-01-24
- added V1.1.1 0002 encoder and V1.1.2 0002 encoder