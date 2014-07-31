pycpu
=====

Github mirror of the original PyCpu on sourceforge.

Running a very small subset of python on an FPGA is possible with pyCPU.

The Python Hardware Processsor (pyCPU)  is a implementation of a Hardware CPU in Myhdl. The CPU can directly execute something very similar to python bytecode (but only a very restricted instruction set). The Programcode for the CPU can therefore be written directly in python (very restricted parts of python). This code is then converted to this restricted python bytecode. Since the hardware description is also in python, the slightly modified bytecode is then automatically loaded into the CPU design.

Most “bytecode” instructions are executed in the Hardware CPU with one instruction per cycle. If you have enought hardware available you can simply instantiate more cores on an FPGA with different Programmcode to make them run in parallel.

For more visit : http://pycpu.wordpress.com/


Please note this is not my code. 
