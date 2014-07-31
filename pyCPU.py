#####################################
# File: pyCPU.py
# Author: Norbert Feurle
# start Date:   2.2.2012 
# latest Edit: 10.2.2013
# 
# Description: Python Hardware Processor 
#        This Code implements a Hardware CPU in myhdl. The code for the CPU is drictly written in python
#        and since the hardware description is also in python, the programmcode is automatically loaded into the design
#        The Simulation of the cpu code on the hardware can be done in python only (only python needed! and the myhdl python library).
#        The bytecode of python is executed in the CPU with normaly one instruction per cycle 
#        You can simply instantiate more cores on an FPGA with different Programmcode to make them run in parallel
#
# License: Pro life licence. 
#    You are not allowed to use this code for any purpose which is in any kind disrespectfully to life and/or freedom
#    In such a case it remains my property
#    for example: You are not allowed to build weapons, or large-scale animal husbandry automation equipment or anything
#                that is used to harm, destroy or is used to frighten living beeings at an unacceptable rate, or build hardware
#                with it where the workers dont get paid appropriate, or any process where the waste issue isnt solved in a sustainable way, 
#                etc..
#    If you use it respectfully you are allowed to use it for free and are welcome to contribute with your changes/extensions
#    You also have to keep this licence.
#################################################################################################

########################################################################################
#### Limitations:
#### no lists, no dicts no tuples, no float, no complex numbers, etc.
#### no classmembers,no multiplication, no exeptions, no for x in xxx:, etc.
########################################################################################
### What is supported:
#---------------------------------------------------
### ints (with x bits), no other python types only plane ints
### if and while (comparisions with  <,>, >=, <=,!=,== ) 
### nested while loops up to CONST_LOOP_DEPTH (Constant Default value = 4)
### assignments to globals or local varibles from const, globals or define local variables
### Operators: +. -, ^ ,~, |, & ,<<,>>
### Simple Digital IOs over PORTS
### Function calls (with consts,and globals, or vars as argument, one intager as return value), no default arguments, no keyword arguments,no other functions as arguments
### up to MAX_NUMBER_FUNCTION_ARGUMENTS (Constant Default value = 10) arguments
### up to CONST_PC_STACK_DEPTH (Constant Default value=5) number of nested function calls
### up to VAR_MEM_DEPTH (Constant Default value=20) local variables
########################################################################################


###################################################################
#####  Bug Track / Upcomming Features list :
#---------------------------------------------
#  (done) Binary operations remove doesnt removes the operands from stack 
#  (done but stack ram could be smaller) (but stack_mem is now very big, Solution -> add some cycles for rot_two, rot_three and rot_for and put stak into a RAM,maybe dualported ) dis.opmap['POP_BLOCK'] and dis.opmap['SETUP_LOOP'] clear stack
#  (halve done) Global memory initilisation in myhdl
#  (done)-> GLOBAL_CONTENT is set to (0,) in this case <- if there is no function exept CPU_main, toVHDL creates an error,probably because Global_mem is empty
#  (done) hasattr(eval(currentfunction.func_code.co_names[actual_Argument]), '__call__') througs exeption if PORTA_IN, etc is note defined global (defining PREDEFINED_IO_ADDRESSES should be enough)
#  TODO MakeProcessorBytecode must give Error if opcode is not supported
#  TODO wheater make PORTS in a all positive range or all with -2**(x-1) to +2**(x-1) conversion from signed to unsigned
#  (done) Functions need to be able to use vars from var_mem as arguments (Dual ported var_mem ram)
#  TODO calling a function with an function as an argument would not work
#  TODO ROT_FOUR is not yet supported, adding a extra cycles is needed
#  TODO Test generated VHDL code, and on an FPGA, also cosimulation
#  TODO More Programm tests, Clean UP code, for example: eliminate magic numbers,general cleanup
#  (done) insert cycle after var_mem is read to make it possible to map it into ram, same for programm_code
#  (done) make jumps to addresses possible which exeed the size of VAR_BITWIDTH, for example to make a usable processor with WORD_SZ=4 bit
#  TODO generic addable multiplication support
#  (done) put constant memory and global memory into one compined memory -> in global mem (saves some luts)
#  TODO check when VAR_BITWIDTH is greater then Bitwidth(Prog_mem_SIZE), if everything works when VAR_BITWIDTH is not 8
########info:
# ROT_TWO after SETUP_LOOP would not work but is kind of usless because the new stack block is empty
##########################################
#################################################################
####### Nice to haves: 
#-----------------------------
#  TODO maybe support List of ints with single integer subscription
#  TODO additional SPI,I2C,Timer,etc modules -> (done) RS232 
#  (done)-> (the complete programm can be loaded via rs232 into the cpu)
#  call functions from extern which are not loaded at startup
#################################################################

import sys
import imp
import os
import math


import MakeProcessorBytecode

###### The File with the Prozessor code  ######
if len(sys.argv)>1:
  Mainfile=sys.argv[1]
else:
  Mainfile="main.py"



### load module from a filename
DDk=imp.load_source(os.path.splitext(Mainfile)[0],os.path.expanduser(Mainfile))

### empty function definition (for type checking) ####
def kkkt():pass

##### create a dictionary from module Variables #########
MD=dict([(i,getattr(DDk,i)) for i in dir(DDk) if not i.startswith('_') ]) 

### assert that the Variable PYCPU_CONFIGS is defined correctly  ####
assert MD.has_key("PYCPU_CONFIGS"), "Error, Variable PYCPU_CONFIGS must be defined"
assert type(MD["PYCPU_CONFIGS"]) is type({}), "Error, Variable PYCPU_CONFIGS must be a dictionary"
assert MD["PYCPU_CONFIGS"].has_key("PREDEFINED_IO_ADDRESSES") , "Error: PYCPU_CONFIGS has no PREDEFINED_IO_ADDRESSES defined"
assert MD["PYCPU_CONFIGS"].has_key("Prog_mem_SIZE") , "Error: PYCPU_CONFIGS has no Prog_mem_SIZE defined"
assert MD["PYCPU_CONFIGS"].has_key("Var_mem_SIZE") , "Error: PYCPU_CONFIGS has no Var_mem_SIZE defined"
assert MD["PYCPU_CONFIGS"].has_key("Globals_mem_SIZE") , "Error: PYCPU_CONFIGS has no Globals_mem_SIZE defined"
assert MD["PYCPU_CONFIGS"].has_key("STACK_SIZE") , "Error: PYCPU_CONFIGS has no STACK_SIZE defined"
assert MD["PYCPU_CONFIGS"].has_key("CPU_BITWIDTH") , "Error: PYCPU_CONFIGS has no CPU_BITWIDTH defined"
assert MD["PYCPU_CONFIGS"].has_key("CPU_RS232_BAUDRATE") , "Error: PYCPU_CONFIGS has no CPU_RS232_BAUDRATE defined"
assert MD["PYCPU_CONFIGS"].has_key("NR_FUNCTION_ARGUMENTS") , "Error: PYCPU_CONFIGS has no NR_FUNCTION_ARGUMENTS defined"
assert MD["PYCPU_CONFIGS"].has_key("NR_NESTED_LOOPS") ,"Error: PYCPU_CONFIGS has no NR_NESTED_LOOPS defined"
assert MD["PYCPU_CONFIGS"].has_key("CPU_CLK_FREQ"), "Error: Clk frequenzy not defined"
assert len(MD["PYCPU_CONFIGS"])==10, "Error , PYCPU_CONFIGS must contain all settings" 


######All config-strings are loaded into this environment as a real variable
for i in MD["PYCPU_CONFIGS"]:
  exec(i+"="+MD["PYCPU_CONFIGS"][i].__repr__())  


GLOBAL_MEM_START=max(PREDEFINED_IO_ADDRESSES.values())+1


#assert CPU_RS232_BAUDRATE in serial.baudrate_constants.keys(), "Error, Baudrate is not supported"
Baudrate_const=CPU_RS232_BAUDRATE


### assert that the code in the file/module has a main function ####
assert MD.has_key("main"), "Error: Prozessor Code has no main function defined"
assert type(MD["main"])==type(kkkt), "Error: Prozessor Code has no main function defined"


#print Prog_mem_SIZE


### Make the data to be written into the pyCpu core ####
ARGUMENT_BITLENGTH=int(math.log(Prog_mem_SIZE-1,2)+1)
#print ARGUMENT_BITLENGTH
ProcessorCodeObject=MakeProcessorBytecode.MakeBytecode(MD["main"],PREDEFINED_IO_ADDRESSES,MD,ARGUMENT_BITLENGTH)



THE_FUNCTION_ADRESSES_START=ProcessorCodeObject.GLOBAL_FUNCTION_ADRESSES_START
GLOBALS_MEM_CONTENT=ProcessorCodeObject.GLOBALS_MEM_CONTENT
THE_PROGRAM=ProcessorCodeObject.THE_PROGRAM
THE_STACK_SIZE=max(STACK_SIZE,ProcessorCodeObject.GLOBAL_STACK_SIZE)  ### get max stacksize 


  
  
##exdend programm to Wanted Ramsize
assert Prog_mem_SIZE>=len(THE_PROGRAM)
THE_PROGRAM=THE_PROGRAM+(0,)*(Prog_mem_SIZE-len(THE_PROGRAM))

##exdend constants to Wanted Ramsize
#assert Constants_mem_SIZE>=len(CONSTANTS_MEM_CONTENT)
#CONSTANTS_MEM_CONTENT=CONSTANTS_MEM_CONTENT+(0,)*(Constants_mem_SIZE-len(CONSTANTS_MEM_CONTENT))

##exdend Globals to Wanted Ramsize
GLOBAL_MEM_START=max(PREDEFINED_IO_ADDRESSES.values())+1
assert (Globals_mem_SIZE-GLOBAL_MEM_START)>=len(GLOBALS_MEM_CONTENT)
GLOBALS_MEM_CONTENT=(0,)*GLOBAL_MEM_START+GLOBALS_MEM_CONTENT+(0,)*(Globals_mem_SIZE-len(GLOBALS_MEM_CONTENT)-GLOBAL_MEM_START)
#print GLOBAL_MEM_START
   #   CONTENT=CONTENT+tuple([0]*(DEPTH-len(CONTENT)))
   # if DEPTH!=None:
   #   assert DEPTH>=len(GLOBAL_CONTENT)
   #   GLOBAL_CONTENT=GLOBAL_CONTENT+tuple([0]*(DEPTH-len(GLOBAL_CONTENT)))


   
###### Start of the Processor myhdl implementation   ############
import sys


from myhdl import *

import math

def DP_RAM(dout, din, addr_wr,addr_rd, we, clk, WORD_SZ=8, DEPTH=16384):
    mem = [Signal(intbv(0,min=-2**(WORD_SZ-1),max=2**(WORD_SZ-1))) for i in range(DEPTH)]

    @always(clk.posedge)
    def write_read():
        if we:
            mem[int(addr_wr)].next = din
        dout.next = mem[int(addr_rd)]
        
    return write_read

    
def ROM(clk,rst,dout,addr,CONTENT,WORD_SZ=8):
    mem = [Signal(intbv(CONTENT[i])[WORD_SZ:]) for i in range(len(CONTENT))]

    @always(clk.posedge)
    def rom_logic():
      dout.next= mem[addr]
    
    return rom_logic,combi_log

    
def RAMg(clk,rst,dout,din,we,addr,CONTENT,WORD_SZ=8):

    if 9<WORD_SZ<19: #seems to be a lattice error
      mem1 = [Signal(intbv(CONTENT[i]&0x1ff)[9:]) for i in range(len(CONTENT))]
      mem2 = [Signal(intbv((CONTENT[i]&0xfffe00)>>9)[WORD_SZ-9:]) for i in range(len(CONTENT))]
      dout1 = Signal(intbv(0)[9:])
      dout2 = Signal(intbv(0)[9:])
      dinXX= Signal(intbv(0)[9:])
      
      @always(clk.posedge)
      def progrom_logic():
	if we:
	  mem1[addr].next = din[9:0]
	  mem2[addr].next = dinXX
	dout2.next=mem2[addr]
	dout1.next=mem1[addr]
	#dout.next=concat(mem2[addr],mem1[addr]) 
	
      @always_comb
      def lol():
	dinXX.next= din[WORD_SZ:9]
	
	dout.next=concat(dout2[WORD_SZ-9:],dout1).signed()
      return progrom_logic,lol
      
    else:

      mem = [Signal(intbv(CONTENT[i])[WORD_SZ:]) for i in range(len(CONTENT))]
      @always(clk.posedge)
      def progrom_logic():
	if we:
	  mem[addr].next = din
	dout.next=mem[addr].signed()    ###TODO
	
      return progrom_logic

def RAM(clk,rst,dout,din,we,addr,CONTENT,WORD_SZ=8):

    if 9<WORD_SZ<19: #seems to be a lattice error
      mem1 = [Signal(intbv(CONTENT[i]&0x1ff)[9:]) for i in range(len(CONTENT))]
      mem2 = [Signal(intbv((CONTENT[i]&0xfffe00)>>9)[9:]) for i in range(len(CONTENT))]
      dout1 = Signal(intbv(0)[9:])
      dout2 = Signal(intbv(0)[9:])
      dinXX= Signal(intbv(0)[9:])
      
      @always(clk.posedge)
      def progrom_logic():
	if we:
	  mem1[addr].next = din[9:0]
	  mem2[addr].next = dinXX
	dout2.next=mem2[addr]
	dout1.next=mem1[addr]
	#dout.next=concat(mem2[addr],mem1[addr]) 
	
      @always_comb
      def lol():
	dinXX.next= din[WORD_SZ:9]
	
	dout.next=concat(dout2[WORD_SZ-9:],dout1)
      return progrom_logic,lol
      
    else:

      mem = [Signal(intbv(CONTENT[i])[WORD_SZ:]) for i in range(len(CONTENT))]
      @always(clk.posedge)
      def progrom_logic():
	if we:
	  mem[addr].next = din
	dout.next=mem[addr].signed()    ###TODO
	
      return progrom_logic

    
    

    
GLOBAL_NUMBERSTACK_OPS=22
STACK_NOP,STACK_ADD,STACK_POSITIVE,STACK_NOT,STACK_NEGATIVE,STACK_INVERT,STACK_RSHIFT,STACK_LSHIFT,STACK_AND,STACK_SUB,STACK_OR,STACK_XOR,STACK_POP,STACK_LOAD,STACK_CMP,STACK_ROT_FOUR, STACK_ROT_TWO, STACK_ROT_THREE_0,STACK_ROT_THREE_1,STACK_DUP_TOP,STACK_SETUP_LOOP,STACK_POP_BLOCK=range(GLOBAL_NUMBERSTACK_OPS)

def Stack(clk,rst,TopData_Out,Data_In,StackOP,CMPmode,WORD_SZ=32,SIZE=4,PROG_SIZE_BITWIDTH=8,NESTED_LOOP_DEPTH=32):
    CONST_LOOP_DEPTH=NESTED_LOOP_DEPTH 
    if SIZE<4:
      SIZE=4
      
    #MODULO_CONST=2**WORD_SZ
    Stack_mem = [Signal(intbv(0,min=-2**(WORD_SZ-1),max=2**(WORD_SZ-1))) for i in range(SIZE*CONST_LOOP_DEPTH)]
    stack_read_addr=Signal(intbv(0,min=0,max=SIZE*CONST_LOOP_DEPTH))
    stack_write_addr=Signal(intbv(0,min=0,max=SIZE*CONST_LOOP_DEPTH))
    TOF_RAM_Data=Signal(intbv(0,min=-2**(WORD_SZ-1),max=2**(WORD_SZ-1)))

    Data_to_REG=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    #Data_to_REG_RD=Signal(intbv(0,min=-2**(WORD_SZ-1),max=2**(WORD_SZ-1)))
    REG_TopOfStack_Data=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    
    
    TOS_pointer=Signal(intbv(0,min=0,max=SIZE))
    TOS_pointer_pre=Signal(intbv(0,min=0,max=SIZE))
    #TOS3_pointer= Signal(intbv(0,min=0,max=SIZE))
    REG_StackOP=Signal(intbv(0,min=0,max=GLOBAL_NUMBERSTACK_OPS))
    REG_CmpMode=Signal(intbv(0,min=0,max=6)) 
    
    enable_stackpointer_increase=Signal(bool(0))
    enable_stackpointer_deacrease=Signal(bool(0))
    enable_stack_write_data=Signal(bool(0))
    
    stack_offset=Signal(intbv(0,min=0,max=SIZE*CONST_LOOP_DEPTH))
    stack_pos_mem=[Signal(intbv(0,min=0,max=SIZE)) for i in range(CONST_LOOP_DEPTH+1)]
    stack_pos_mem_addr=Signal(intbv(0,min=0,max=CONST_LOOP_DEPTH+1))
    SaveStack_pos=Signal(bool(0))
    ReturnToStack_pos=Signal(bool(0))
    #SaveStack_pos_function=Signal(bool(0))
    @always(clk.posedge,rst.negedge)
    def seq_logic():
        if rst == 0:
            TOS_pointer.next=0
            stack_pos_mem_addr.next=0
            stack_offset.next=0
            REG_StackOP.next=STACK_NOP
            REG_CmpMode.next=0
        else:
            if enable_stackpointer_increase:
                TOS_pointer.next=(TOS_pointer+1)%SIZE
            
            if enable_stackpointer_increase or enable_stack_write_data:
                Stack_mem[int(stack_write_addr)].next=Data_to_REG
            
            if enable_stackpointer_deacrease:
                TOS_pointer.next=(TOS_pointer-1)%SIZE

            if SaveStack_pos:
                #print "####### Save stack pos:",TOS_pointer
                stack_pos_mem[int(stack_pos_mem_addr)].next=TOS_pointer
                stack_pos_mem_addr.next=stack_pos_mem_addr+1
                stack_offset.next=stack_offset+SIZE
            if ReturnToStack_pos:
                #print "####### Return stack pos:",TOS_pointer_pre
                TOS_pointer.next=TOS_pointer_pre
                stack_pos_mem_addr.next=stack_pos_mem_addr-1
                stack_offset.next=stack_offset-SIZE
            TOS_pointer_pre.next=(stack_pos_mem[int(stack_pos_mem_addr-1)])
        #    if StackOP==STACK_LOAD:
        #        REG_TopOfStack_Data.next=Data_In
            #else:
            REG_TopOfStack_Data.next=Data_to_REG
            REG_StackOP.next=StackOP
            REG_CmpMode.next= CMPmode
            TOF_RAM_Data.next=Stack_mem[int(stack_read_addr)]

    #@always_comb
    #def comb_logic2():
        
        
        #TOS_Data_RD.next#=Stack_mem[int(TOS_pointer+stack_offset)]
        #TOS1_Data_RD.next=Stack_mem[int(TOS1_pointer+stack_offset)]
        #TOS2_Data_RD.next=Stack_mem[int(TOS2_pointer+stack_offset)]
        #TopData_Out.next=Data_to_REG #Stack_mem[int(TOS_pointer+stack_offset)]
            
    @always_comb
    def comb_logic():
        #Data_to_REG_RD.next=REG_TopOfStack_Data
        stack_write_addr.next=TOS_pointer+stack_offset
        stack_read_addr.next=((TOS_pointer-1)%SIZE)+stack_offset
        
        
        #Data_to_stackmem.next=REG_TopOfStack_Data
        Data_to_REG.next=REG_TopOfStack_Data
        #TOS_Data.next=REG_TopOfStack_Data
        TopData_Out.next=REG_TopOfStack_Data
        #TopData_Out.next=0
        
        SaveStack_pos.next=False
        ReturnToStack_pos.next=False
        enable_stackpointer_increase.next=1
        enable_stackpointer_deacrease.next=0
        enable_stack_write_data.next=0
        
        if REG_StackOP==STACK_LOAD:
            Data_to_REG.next=Data_In
            TopData_Out.next=Data_In
        elif REG_StackOP==STACK_POP:
            TopData_Out.next=TOF_RAM_Data
            Data_to_REG.next=TOF_RAM_Data
        elif REG_StackOP==STACK_ADD:
            Data_to_REG.next=TOF_RAM_Data+REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data+REG_TopOfStack_Data
        elif REG_StackOP==STACK_POSITIVE:  #???
            Data_to_REG.next=REG_TopOfStack_Data
            TopData_Out.next=REG_TopOfStack_Data
            #TOS_Data.next=TOS_Data_RD
        elif REG_StackOP==STACK_NOT:
            Data_to_REG.next=not REG_TopOfStack_Data
            TopData_Out.next=not REG_TopOfStack_Data
            #TOS_Data.next=TOS_Data_RD
        elif REG_StackOP==STACK_NEGATIVE:
            Data_to_REG.next=-REG_TopOfStack_Data
            TopData_Out.next=-REG_TopOfStack_Data
            #TOS_Data.next=-TOS_Data_RD
        elif REG_StackOP==STACK_INVERT:
            Data_to_REG.next=~REG_TopOfStack_Data
            TopData_Out.next=~REG_TopOfStack_Data
            #TOS_Data.next=~TOS_Data_RD
        elif REG_StackOP==STACK_RSHIFT:
            Data_to_REG.next=TOF_RAM_Data>>REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data>>REG_TopOfStack_Data
            #TOS1_Data.next=TOS1_Data_RD>>TOS_Data_RD
        elif REG_StackOP==STACK_LSHIFT:
            Data_to_REG.next=TOF_RAM_Data<<REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data<<REG_TopOfStack_Data
            #TOS1_Data.next=TOS1_Data_RD<<TOS_Data_RD
        elif REG_StackOP==STACK_AND:
            Data_to_REG.next=TOF_RAM_Data&REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data&REG_TopOfStack_Data
            #TOS1_Data.next=TOS1_Data_RD&TOS_Data_RD
        elif REG_StackOP==STACK_SUB:
            Data_to_REG.next=TOF_RAM_Data-REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data-REG_TopOfStack_Data
            #TOS1_Data.next=TOS1_Data_RD-TOS_Data_RD
        elif REG_StackOP==STACK_OR:
            Data_to_REG.next=TOF_RAM_Data|REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data|REG_TopOfStack_Data
        elif REG_StackOP==STACK_XOR:
            Data_to_REG.next=TOF_RAM_Data^REG_TopOfStack_Data
            TopData_Out.next=TOF_RAM_Data^REG_TopOfStack_Data
        elif REG_StackOP==STACK_ROT_TWO:
            TopData_Out.next=TOF_RAM_Data
            Data_to_REG.next=TOF_RAM_Data
        elif REG_StackOP==STACK_ROT_THREE_1:
            TopData_Out.next=TOF_RAM_Data
            Data_to_REG.next=TOF_RAM_Data
        #elif REG_StackOP==STACK_DUP_TOP:   
        #    TopData_Out.next=REG_TopOfStack_Data  #is standard assignment
        #    Data_to_REG.next=REG_TopOfStack_Data  
        elif REG_StackOP==STACK_POP_BLOCK:
            TopData_Out.next=TOF_RAM_Data
            Data_to_REG.next=TOF_RAM_Data
        elif REG_StackOP==STACK_CMP:
            if REG_CmpMode==0: #operator <
              if TOF_RAM_Data<REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0
            if REG_CmpMode==1: #operator <=
              if TOF_RAM_Data<=REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0
            if REG_CmpMode==2:  #operator ==  
              if TOF_RAM_Data==REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0
            if REG_CmpMode==3: #operator !=
              if TOF_RAM_Data!=REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0
            if REG_CmpMode==4: #operator >
              if TOF_RAM_Data>REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0
            if REG_CmpMode==5: #operator >=
              if TOF_RAM_Data>=REG_TopOfStack_Data:
                  Data_to_REG.next=1
                  TopData_Out.next=1
              else:
                  Data_to_REG.next=0
                  TopData_Out.next=0    
            
            
        
        if StackOP==STACK_NOP:
            enable_stackpointer_increase.next=0
        elif StackOP==STACK_SETUP_LOOP:
            enable_stackpointer_increase.next=1
            SaveStack_pos.next=True
        elif StackOP==STACK_POP_BLOCK:
            stack_read_addr.next=((TOS_pointer_pre)%SIZE)+(stack_offset-SIZE)
            enable_stackpointer_increase.next=0
            ReturnToStack_pos.next=True 
        elif StackOP==STACK_POSITIVE:  #???
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            #TOS_Data.next=TOS_Data_RD
        elif StackOP==STACK_NOT:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            #TOS_Data.next=TOS_Data_RD
        elif StackOP==STACK_NEGATIVE:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            #TOS_Data.next=-TOS_Data_RD
        elif StackOP==STACK_INVERT:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            #TOS_Data.next=~TOS_Data_RD
        elif StackOP==STACK_ADD:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD+TOS_Data_RD
        elif StackOP==STACK_RSHIFT:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD>>TOS_Data_RD
        elif StackOP==STACK_LSHIFT:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD<<TOS_Data_RD
        elif StackOP==STACK_AND:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD&TOS_Data_RD
        elif StackOP==STACK_SUB:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD-TOS_Data_RD
        elif StackOP==STACK_OR:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD|TOS_Data_RD
        elif StackOP==STACK_XOR:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
            #TOS1_Data.next=TOS1_Data_RD^TOS_Data_RD
        elif StackOP==STACK_POP:
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=1
      # elif StackOP==STACK_CALL_FUNCTION:
        #    enable_stackpointer_increase.next=0
        #    enable_stackpointer_deacrease.next=1  #pop function address
        #    SaveStack_pos_function.next=True
        elif StackOP==STACK_LOAD:
            enable_stackpointer_increase.next=1
            enable_stackpointer_deacrease.next=0
            #TopOfStack_Data.next=Data_In

        elif StackOP==STACK_ROT_TWO: 
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            enable_stack_write_data.next=1
            stack_write_addr.next=((TOS_pointer-1)%SIZE)+stack_offset
            #TOS_Data.next=TOS1_Data_RD
            #TOS1_Data.next=TOS_Data_RD
        elif StackOP==STACK_ROT_THREE_0:  
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            enable_stack_write_data.next=1
            stack_write_addr.next=((TOS_pointer-2)%SIZE)+stack_offset
            stack_read_addr.next=((TOS_pointer-2)%SIZE)+stack_offset
        elif StackOP==STACK_ROT_THREE_1:  
            enable_stackpointer_increase.next=0
            enable_stackpointer_deacrease.next=0
            enable_stack_write_data.next=1
            Data_to_REG.next=TOF_RAM_Data
            stack_write_addr.next=((TOS_pointer-1)%SIZE)+stack_offset
            stack_read_addr.next=((TOS_pointer-1)%SIZE)+stack_offset
            #TOS_Data.next=TOS1_Data_RD
            #TOS1_Data.next=TOS2_Data_RD
            #TOS2_Data.next=TOS_Data_RD
        #elif StackOP==STACK_ROT_FOUR:  ##TODO
        #TOS_Data.next=Stack_mem[int(TOS_pointer)]
        #   TOS1_Data.next=Stack_mem[int(TOS1_pointer)]
          #  TOS2_Data.next=Stack_mem[int(TOS2_pointer)]        
        elif StackOP==STACK_DUP_TOP:
          enable_stackpointer_increase.next=1
          enable_stackpointer_deacrease.next=0    
        elif StackOP==STACK_CMP:
          enable_stackpointer_increase.next=1
          enable_stackpointer_deacrease.next=0

        else:
            enable_stackpointer_increase.next=0
        
        
        

            
    return seq_logic,comb_logic#,comb_logic2
    

def UsignedtoSigned(val,BIT_WIDTH):
  return val-(val>>(BIT_WIDTH-1))*2**BIT_WIDTH

import RS232_Norbo
import RS232Programmer



def IOGlobalModule(clk,rst,dout,din,addr,we,\
            PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,\
            iData_RS232,WriteEnable_RS232, oWrBuffer_full_RS232,oData_RS232,read_addr_RS232,rx_addr_RS232, # iRX needs to initialized with 1 \
            GLOBAL_CONTENT,WIDTH=32,Clkfrequenz=12e6,PROG_SIZE_BITWIDTH=8):
    
    RX_BUFF_LEN=read_addr_RS232.max
    
    Sync_in1_PORTA=Signal(intbv(0)[WIDTH:])
    Sync_in2_PORTA=Signal(intbv(0)[WIDTH:])
    Sync_in1_PORTB=Signal(intbv(0)[WIDTH:])
    Sync_in2_PORTB=Signal(intbv(0)[WIDTH:])
    
    INTERN_PORTC_OUT=Signal(intbv(0)[WIDTH:])
    INTERN_PORTD_OUT=Signal(intbv(0)[WIDTH:])
    addr_last=Signal(intbv(0,min=addr.min,max=addr.max))
    dout_intern=Signal(intbv(0,min=dout.min,max=dout.max))

    ####Globals memory #####
    #TODO unsigned to sind with this bitwidth only fits to addresses groesser function_address_start
    #glob_mem = [Signal(intbv(UsignedtoSigned(GLOBAL_CONTENT[i],PROG_SIZE_BITWIDTH),min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1))) for i in range(len(GLOBAL_CONTENT))]
    globalRAM_dout=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    globalRAM_din=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    globalRAM_we=Signal(bool(0))
    #THA_CONTENT_GLOBAL_MOD= tuple((0,)*10+GLOBAL_CONTENT) #map(lambda val: UsignedtoSigned(val,PROG_SIZE_BITWIDTH),
    globalRAM_addr=Signal(intbv(0,min=0,max=len(GLOBAL_CONTENT)))
    
    
    globalRAM_inst=RAMg(clk,rst,globalRAM_dout,globalRAM_din,globalRAM_we,globalRAM_addr,CONTENT=GLOBAL_CONTENT,WORD_SZ=PROG_SIZE_BITWIDTH)
    
    ######RS232 Module#########
    ##### Signal definitions #####
    reg_read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    
    ##### Instanciate RS232 Module #####
    #rs232_instance=RS232_Norbo.RS232_Module(clk,rst,iRX,oTX, iData_RS232,WriteEnable_RS232,  \
    #    oWrBuffer_full_RS232,oData_RS232,read_addr_RS232,rx_addr_RS232,Clkfrequenz=Clk_f,  \
    #    Baudrate=BAUDRATE,RX_BUFFER_LENGTH=RX_BUFF_LEN,TX_BUFFER_LENGTH=TX_BUFF_LEN)
    
    
    #Bufflength=2
    #iRX_9=Signal(bool(1))
    #WriteEnable_RS232_9=Signal(bool(0))
    #oWrBuffer_full_RS232_9=Signal(bool(0))
    #iData_RS232_9=Signal(intbv(0)[9:])
    #oData_RS232_9=Signal(intbv(0)[9:])
    #read_addr_RS232_9=Signal(intbv(0,min=0,max=Bufflength))
    #rx_addr_RS232_9=Signal(intbv(0,min=0,max=Bufflength))
    ##### Instanziate RS232 9 Bit Module #####
    #rs232_instance9=RS232_Bitmode.RS232_Module(clk,rst,iRX_9,oTX_9, iData_RS232_9,WriteEnable_RS232_9,  \
    #     oWrBuffer_full_RS232_9,oData_RS232_9,read_addr_RS232_9,rx_addr_RS232_9,Clkfrequenz=Clkfrequenz,  \
    #     Baudrate=625000,RX_BUFFER_LENGTH=Bufflength,TX_BUFFER_LENGTH=Bufflength)
    
    
    
    
    
    
    @always_comb
    def rs232_read_buffer_addr():
      globalRAM_we.next=we
      globalRAM_din.next=din
      globalRAM_addr.next=addr
      
      #iRX_9.next=True
      if we and (addr==5):
        read_addr_RS232.next=din[WIDTH:]%RX_BUFF_LEN
      else:
        read_addr_RS232.next=reg_read_addr_RS232
      
      if addr_last>=8:
	dout.next=globalRAM_dout
      else:
	dout.next=dout_intern
    
    @always(clk.posedge,rst.negedge)
    def IO_write_sync():
      if rst==0:
        INTERN_PORTC_OUT.next=0
        INTERN_PORTD_OUT.next=0
      else:
        Sync_in1_PORTA.next=PORTA_IN
        Sync_in2_PORTA.next=Sync_in1_PORTA

        Sync_in1_PORTB.next=PORTB_IN
        Sync_in2_PORTB.next=Sync_in1_PORTB
        WriteEnable_RS232.next=0
        #WriteEnable_RS232_9.next=0
        if we:
          if addr==2:
            INTERN_PORTC_OUT.next=din[WIDTH:]
          if addr==3:
            INTERN_PORTD_OUT.next=din[WIDTH:]
          if addr==4:
            WriteEnable_RS232.next=1
            iData_RS232.next=din[WIDTH:]
          if addr==5:
            reg_read_addr_RS232.next=din[WIDTH:]
          
          #if addr==8:
	  #  WriteEnable_RS232_9.next=1
          #  iData_RS232_9.next=concat(INTERN_PORTC_OUT[7],din[WIDTH:])
            
          #if addr>=10:
          #  glob_mem[int(addr-10)].next=din
            #GLOBAL_CONTENT[int(addr-4)]
              
    @always(clk.posedge)
    def IO_read():
        PORTC_OUT.next=INTERN_PORTC_OUT
        PORTD_OUT.next=INTERN_PORTD_OUT
        addr_last.next=addr
        dout_intern.next = 0
        if addr==0:
          dout_intern.next = Sync_in2_PORTA[WIDTH:].signed()
        if addr==1:
          dout_intern.next = Sync_in2_PORTB[WIDTH:].signed()
        if addr==2:
          dout_intern.next = INTERN_PORTC_OUT[WIDTH:].signed()
        if addr==3:
          dout_intern.next = INTERN_PORTD_OUT[WIDTH:].signed()
        if addr==4:
          dout_intern.next = oData_RS232
        if addr==5:
          dout_intern.next = reg_read_addr_RS232
        if addr==6:
          dout_intern.next = rx_addr_RS232
        if addr==7:
          dout_intern.next = oWrBuffer_full_RS232
        #if addr==9:
	 # dout_intern.next = oWrBuffer_full_RS232_9
        #if addr>=10:
	  
         # dout_intern.next = glob_mem[int(addr-10)] # globalRAM_dout #
          
    return IO_write_sync,IO_read,rs232_read_buffer_addr,globalRAM_inst
    
    
def Processor(clk,rst,CpuUsesRam,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX,CPU_PROGRAM=THE_PROGRAM,CPU_ARG_BITLENGTH=ARGUMENT_BITLENGTH,CPU_GLOBALS=GLOBALS_MEM_CONTENT,CONST_FUNCTION_ADRESSES_START=THE_FUNCTION_ADRESSES_START,VAR_BITWIDTH=CPU_BITWIDTH,VAR_MEM_DEPTH=Var_mem_SIZE,STACK_SIZE=THE_STACK_SIZE,CLK_F=CPU_CLK_FREQ,RS232_BAUDRATE=Baudrate_const,MAX_NUMBER_FUNCTION_ARGUMENTS=NR_FUNCTION_ARGUMENTS,NR_NESTED_LOOPS=NR_NESTED_LOOPS,DEBUG_OUTPUT=False):

    CONST_PROGRAMM_LENGTH=len(CPU_PROGRAM)
    PROG_SIZE_BITWIDTH=max(int(math.log(CONST_PROGRAMM_LENGTH-1,2))+1,VAR_BITWIDTH)
    
    NUMBER_OF_SELECTS=4
    ENUM_SEL_NONE,ENUM_SEL_VARIABLE,ENUM_SEL_CONST,ENUM_SEL_GLOBAL=range(NUMBER_OF_SELECTS)
    
    StackTopSel=Signal(intbv(0,min=0,max=NUMBER_OF_SELECTS))
    REG_StackTopSel=Signal(intbv(0,min=0,max=NUMBER_OF_SELECTS))
    
    
    NUMBER_FROM_SELECTS=4
    FROM_NONE,FROM_CONST,FROM_GLOBAL,FROM_VAR=range(NUMBER_FROM_SELECTS)
    
    argnext_store=Signal(intbv(0,min=0,max=NUMBER_FROM_SELECTS))
    REG_argnext_store=Signal(intbv(0,min=0,max=NUMBER_FROM_SELECTS))
    

    #### helping signals
    #MAX_NUMBER_FUNCTION_ARGUMENTS=14 # magic number
    #EnableJump=Signal(bool(0))
    Inc_ArgumentCount=Signal(bool(0))
    Clear_ArgumentCount=Signal(bool(0))
    REG_ArgumentCount=Signal(intbv(0,min=0,max=MAX_NUMBER_FUNCTION_ARGUMENTS+2))
    
    programmRAM_addr=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH+1)) #max=Prog_mem_SIZE
    programmRAM_addr_inst=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH+1))
    #programmRAM_addr_wr=Signal(intbv(0)[8:])
    programmRAM_dout=Signal(intbv(0)[8+CPU_ARG_BITLENGTH:]) #first 8 bit is opcode then comes the argument
    programmRAM_din=Signal(intbv(0)[8+CPU_ARG_BITLENGTH:]) ## 8 is opcode length
    programmRAM_din_inst=Signal(intbv(0)[8+CPU_ARG_BITLENGTH:])
    programmRAM_we=Signal(bool(0))
    programmRAM_we_inst=Signal(bool(0))
    
    MAX_SUB_CYCLES=2
    REG_sub_pc_count=Signal(intbv(0,min=0,max=MAX_SUB_CYCLES))
    sub_pc_count_next=Signal(intbv(0,min=0,max=MAX_SUB_CYCLES))
    
    Push_Programcounter=Signal(bool(0))
    Pop_Programcounter=Signal(bool(0))
    Old_ProgrammCounter=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH))
    REG_PC_offsetValue=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH))
    PC_offsetValue=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH))
    Old_PC_offsetValue=Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH))
    
    Set_Variables_offset=Signal(bool(0))
    #Return_Variables_offset=Signal(bool(0))
    
    #### Programm Memory Signals
    Opcode=Signal(intbv(0)[8:])
    Arg1=Signal(intbv(0)[CPU_ARG_BITLENGTH:])
    REG_ProgramCounter=Signal(intbv(-1,min=-1,max=CONST_PROGRAMM_LENGTH))
    
    
    
    #### Constants Memory Signals
    #constantsRAM_dout=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1)))
    #constantsRAM_addr=Signal(intbv(0,min=0,max=len(CPU_CONSTANTS)))
    #constantsRAM_addr_inst=Signal(intbv(0,min=0,max=len(CPU_CONSTANTS)))
    #constantsRAM_din=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1)))
    #constantsRAM_din_inst=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1)))
    #constantsRAM_we=Signal(bool(0))
    #constantsRAM_we_inst=Signal(bool(0))
    
    #### Programm Variables RAM Signals
    varRAM_dout=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    varRAM_din=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    VariablesAddr=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    varRAM_addr_wr=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    varRAM_addr_rd=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    REG_max_Variables_address=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    Old_max_Variables_address=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    REG_Variables_addr_offset=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    Old_Variables_addr_offset=Signal(intbv(0,min=0,max=VAR_MEM_DEPTH))
    varRAM_we=Signal(bool(0))
    
    #### Stack Signals
    # STACK_SIZE
    #Stack_DataIn=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    #StackValue0=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    ### welches ist goesser log(CONST_PROGRAMM_LENGTH,2)+1  or VAR_BITWIDTH
    Stack_DataIn=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    StackValue0=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1)))
    
    StackOP=Signal(intbv(0,min=0,max=GLOBAL_NUMBERSTACK_OPS))
    StackOP_CMPmode=Signal(intbv(0,min=0,max=6)) 
    
    #### IO Module Signals
    NR_IO_ADDRESSES=max(PREDEFINED_IO_ADDRESSES.values())+1 #
    IO_MODULE_LENGTH_MAX=NR_IO_ADDRESSES+len(GLOBALS_MEM_CONTENT)+1
    CONST_FUNCTION_ADRESSES_START  # <-- is a parameter of the processor unit
    IO_dout=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    IO_din=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    IO_addr=Signal(intbv(0,min=0,max=IO_MODULE_LENGTH_MAX))
    IO_we=Signal(bool(0))
    IO_din_inst=Signal(intbv(0,min=-2**(PROG_SIZE_BITWIDTH-1),max=2**(PROG_SIZE_BITWIDTH-1))) #Signal(intbv(0)[VAR_BITWIDTH:])
    IO_addr_inst=Signal(intbv(0,min=0,max=IO_MODULE_LENGTH_MAX))
    IO_we_inst=Signal(bool(0))
    
    
    
    #########RS232 module###################    
    
    RX_BUFF_LEN=8
    TX_BUFF_LEN=2    
    iData_RS232=Signal(intbv(0)[8:])
    oData_RS232=Signal(intbv(0)[8:])
    WriteEnable_RS232=Signal(bool(0))
    oWrBuffer_full_RS232=Signal(bool(0))
    read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    rx_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))

    
    ##### Instanciate RS232 Module #####
    rs232_instance=RS232_Norbo.RS232_Module(clk,rst,iRX,oTX, \
        iData_RS232 ,WriteEnable_RS232, oWrBuffer_full_RS232,oData_RS232,read_addr_RS232,rx_addr_RS232, \
        Clkfrequenz=CLK_F,Baudrate=RS232_BAUDRATE,RX_BUFFER_LENGTH=RX_BUFF_LEN,TX_BUFFER_LENGTH=TX_BUFF_LEN)

    ####### end RS232 module #################
    
    
    ####################Data Memories #################################

    #    Prog_mem_SIZE=
    #
    #Constants_mem_SIZE=
    #Globals_mem_SIZE=

    
    ####Variables RAM instantiation
    VariablesRAM_inst=DP_RAM(varRAM_dout, varRAM_din, varRAM_addr_wr,varRAM_addr_rd, varRAM_we, clk, WORD_SZ=VAR_BITWIDTH, DEPTH=VAR_MEM_DEPTH)
    
    ####Programm Code Memory instantiation
    ProgrammCode_inst=RAM(clk,rst,programmRAM_dout,programmRAM_din_inst,programmRAM_we_inst,programmRAM_addr_inst,CONTENT=CPU_PROGRAM , WORD_SZ=8+CPU_ARG_BITLENGTH)
    
    ####Constants memory instantiation
    #ConstantsRAM_inst=RAM(clk,rst,constantsRAM_dout,constantsRAM_din_inst,constantsRAM_we_inst,constantsRAM_addr_inst,CONTENT=CPU_CONSTANTS,WORD_SZ=VAR_BITWIDTH)
    
    
    
    
    io_iData_RS232=Signal(intbv(0)[8:])
    #io_oData_RS232=Signal(intbv(0)[8:])
    io_WriteEnable_RS232=Signal(bool(0))
    #io_oWrBuffer_full_RS232=Signal(bool(0))
    io_read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    #io_rx_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    
    
    ###I/O Module GlobalMemory instantiation (IO Port is a global memory)
    IOModule_inst=IOGlobalModule(clk,rst,IO_dout,IO_din_inst,IO_addr_inst,IO_we_inst, \
                         PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT, \
                         io_iData_RS232,io_WriteEnable_RS232, oWrBuffer_full_RS232,oData_RS232,io_read_addr_RS232,rx_addr_RS232,\
                         GLOBAL_CONTENT=CPU_GLOBALS,WIDTH=VAR_BITWIDTH,Clkfrequenz=CLK_F,PROG_SIZE_BITWIDTH=PROG_SIZE_BITWIDTH)
    #####################End Data Memories ###########################
    
    
    ###The stack
    TheStack_inst=Stack(clk,rst,StackValue0,Stack_DataIn,StackOP,StackOP_CMPmode, WORD_SZ=VAR_BITWIDTH,SIZE=STACK_SIZE,PROG_SIZE_BITWIDTH=PROG_SIZE_BITWIDTH,NESTED_LOOP_DEPTH=NR_NESTED_LOOPS)
    
    
    CONST_PC_STACK_DEPTH=5 #Defines how many nested function are possible TODO magic number
    REG_pc_stack_addr=Signal(intbv(0,min=0,max=CONST_PC_STACK_DEPTH))
    pc_steck_mem = [Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH)) for i in range(CONST_PC_STACK_DEPTH)]
    pc_offsets_mem = [Signal(intbv(0,min=0,max=CONST_PROGRAMM_LENGTH)) for i in range(CONST_PC_STACK_DEPTH)]
    max_var_addr_mem=[Signal(intbv(0,min=0,max=VAR_MEM_DEPTH)) for i in range(CONST_PC_STACK_DEPTH)]
    
    
    
    WidthInfo=Signal(intbv(0x11)[8:])
    RS232programmer_data=Signal(intbv(0)[32:])
    RS232programmer_addr=Signal(intbv(0)[32:])
    RS232programmer_we=Signal(bool(0))
   
   
    
    prog_iData_RS232=Signal(intbv(0)[8:])
    #prog_oData_RS232=Signal(intbv(0)[8:])
    prog_WriteEnable_RS232=Signal(bool(0))
    #prog_oWrBuffer_full_RS232=Signal(bool(0))
    prog_read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    #prog_rx_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    programmer_enable=Signal(bool(0))
    
   
    RS232Programmer_inst=RS232Programmer.RS232Programmer(clk,rst,programmer_enable,WidthInfo, \
                       RS232programmer_data,RS232programmer_addr,RS232programmer_we, \
                       prog_iData_RS232,prog_WriteEnable_RS232, oWrBuffer_full_RS232,oData_RS232,prog_read_addr_RS232,rx_addr_RS232)
    

    
    
    #LENGTH_INFO_REGS=10
    INFOREGS_CONTENT= (CONST_FUNCTION_ADRESSES_START,STACK_SIZE,0)
    InfoRegsList=[Signal(intbv(INFOREGS_CONTENT[i],min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1)))  for i in range(len(INFOREGS_CONTENT))]
    infoREGs_din=Signal(intbv(0,min=-2**(VAR_BITWIDTH-1),max=2**(VAR_BITWIDTH-1)))
    infoREGs_addr=Signal(intbv(0,min=0,max=len(INFOREGS_CONTENT)))
    infoREGs_we=Signal(bool(0))
    
    
    #InfoRegsList[0]= CONST_FUNCTION_ADRESSES_START
    
    @always_comb
    def muxRAMtoRS232Programmer():
      IO_din_inst.next=0
      IO_addr_inst.next=0
      IO_we_inst.next=False
      #constantsRAM_din_inst.next=0
      #constantsRAM_addr_inst.next=0
      #constantsRAM_we_inst.next=False
      programmRAM_din_inst.next=0
      programmRAM_addr_inst.next=0
      programmRAM_we_inst.next=False
      infoREGs_din.next=0
      infoREGs_addr.next=0
      infoREGs_we.next=False
      
      programmer_enable.next=False
      
      iData_RS232.next=io_iData_RS232
      WriteEnable_RS232.next=io_WriteEnable_RS232
      read_addr_RS232.next=io_read_addr_RS232
      
      if CpuUsesRam==True:
        programmer_enable.next=False
        iData_RS232.next=io_iData_RS232
        WriteEnable_RS232.next=io_WriteEnable_RS232
        read_addr_RS232.next=io_read_addr_RS232
        IO_din_inst.next=IO_din
        IO_addr_inst.next=IO_addr
        IO_we_inst.next=IO_we
        #constantsRAM_din_inst.next=0 #constantsRAM_din
        #constantsRAM_addr_inst.next=constantsRAM_addr
        #constantsRAM_we_inst.next=False #constantsRAM_we
        programmRAM_din_inst.next=0 #programmRAM_din
        programmRAM_addr_inst.next=programmRAM_addr
        programmRAM_we_inst.next=False #programmRAM_we
      else:  ## RS232 programmer accesses ram#  
        ### mux rs232
        programmer_enable.next=True
        iData_RS232.next=prog_iData_RS232
        WriteEnable_RS232.next=prog_WriteEnable_RS232
        read_addr_RS232.next=prog_read_addr_RS232
        ### top to bits are RAM selecters
        programmRAM_din_inst.next=RS232programmer_data
        programmRAM_addr_inst.next=RS232programmer_addr
        #constantsRAM_din_inst.next=RS232programmer_data
        #constantsRAM_addr_inst.next=RS232programmer_addr
        IO_din_inst.next=RS232programmer_data
        IO_addr_inst.next=RS232programmer_addr
        infoREGs_din.next=RS232programmer_data
        infoREGs_addr.next=RS232programmer_addr
        if (WidthInfo[8:6]==0):
          programmRAM_we_inst.next=RS232programmer_we
        #if (WidthInfo[8:6]==1):
        #  constantsRAM_we_inst.next=RS232programmer_we
        if (WidthInfo[8:6]==2):
          IO_we_inst.next=RS232programmer_we
        if (WidthInfo[8:6]==3):
          infoREGs_we.next=RS232programmer_we
    
    
    
    @always(clk.posedge)
    def InfoREGSRAM():
      if infoREGs_we:
        InfoRegsList[infoREGs_addr].next=infoREGs_din
          
          
    @always_comb
    def splitOpcodeArg():
      Opcode.next= programmRAM_dout[8+CPU_ARG_BITLENGTH:CPU_ARG_BITLENGTH] #OPCODE_CONTENT[int(addr)]
      Arg1.next= programmRAM_dout[CPU_ARG_BITLENGTH:0] #OPCODE_ARGUMENTS_CONTENT[int(addr)]
      if CpuUsesRam==False:
        Opcode.next=9 #NOP operation
    
    
    
    
    @always(clk.posedge,rst.negedge)
    def seq_logic():
        if rst == 0:
            ##### REG_ProgramCounter Part ########
            REG_ProgramCounter.next = -1 #TODO very not nice
            ##### END REG_ProgramCounter Part ########
            REG_ArgumentCount.next=0
            
            REG_max_Variables_address.next=0
            REG_Variables_addr_offset.next=0
            REG_pc_stack_addr.next=0
            REG_PC_offsetValue.next=0
            REG_StackTopSel.next=ENUM_SEL_NONE
            REG_sub_pc_count.next=0
        else:
            if Inc_ArgumentCount==True:
              REG_ArgumentCount.next=REG_ArgumentCount+1
                  
            if Clear_ArgumentCount==True:
              REG_ArgumentCount.next=0

            if varRAM_addr_wr>=REG_max_Variables_address:
              REG_max_Variables_address.next=varRAM_addr_wr+1
              #print "REG_max_Variables_address",REG_max_Variables_address
          
            REG_StackTopSel.next=StackTopSel
            REG_argnext_store.next=argnext_store
            ##### REG_ProgramCounter Part ########
            #if EnableJump==True:
            REG_ProgramCounter.next=programmRAM_addr
            #else:
            # REG_ProgramCounter.next = REG_ProgramCounter+1
              
            REG_PC_offsetValue.next=PC_offsetValue
            ##### END REG_ProgramCounter Part ########
            REG_sub_pc_count.next=sub_pc_count_next
            ##### Programmm counter stack#######
            if Push_Programcounter:                # Set at CALL_FUNCTION
              pc_steck_mem[int(REG_pc_stack_addr-1)].next=REG_ProgramCounter
              pc_offsets_mem[int(REG_pc_stack_addr-1)].next=REG_PC_offsetValue
            if Pop_Programcounter:                # Set at RETURN_VALUE
              REG_pc_stack_addr.next=REG_pc_stack_addr-1
              REG_Variables_addr_offset.next=Old_Variables_addr_offset  
              REG_max_Variables_address.next=Old_max_Variables_address
              #print "########returning REG_max_Variables_address:", REG_max_Variables_address,Old_max_Variables_address,Old_Variables_addr_offset
            #####End Programmm counter stack#########    
            
            if Set_Variables_offset: # Set at LOAD_GLOBAL if a function address is loaded
              REG_pc_stack_addr.next=REG_pc_stack_addr+1
              max_var_addr_mem[int(REG_pc_stack_addr)].next=REG_max_Variables_address
              REG_Variables_addr_offset.next=REG_max_Variables_address
              #print "###########LOAD_GLOBAL",REG_Variables_addr_offset, REG_max_Variables_address,REG_ProgramCounter,programmRAM_addr
            #if Return_Variables_offset:
              
              
    @always_comb
    def comb_logic2():
        
        varRAM_addr_wr.next=REG_Variables_addr_offset+VariablesAddr
        #print "VariablesAddr",VariablesAddr, "REG_Variables_addr_offset",REG_Variables_addr_offset
        Old_ProgrammCounter.next=0
        Old_max_Variables_address.next=0
        Old_Variables_addr_offset.next=0
        Old_PC_offsetValue.next=0
        if REG_pc_stack_addr>0:
          Old_PC_offsetValue.next=pc_offsets_mem[int(REG_pc_stack_addr-1)]
          Old_ProgrammCounter.next=pc_steck_mem[int(REG_pc_stack_addr-1)]
          Old_max_Variables_address.next=max_var_addr_mem[int(REG_pc_stack_addr-1)]
        if REG_pc_stack_addr>1:
          Old_Variables_addr_offset.next=max_var_addr_mem[int(REG_pc_stack_addr-2)]
    

    
    ##### Opcode handling#############
    @always_comb
    def comb_logic():
        sub_pc_count_next.next=0
        varRAM_addr_rd.next=varRAM_addr_wr
        #Enable_PC_offset.next=False
        PC_offsetValue.next=REG_PC_offsetValue 
        Set_Variables_offset.next=False
        #Return_Variables_offset.next=False
        Push_Programcounter.next=False
        Pop_Programcounter.next=False
        Inc_ArgumentCount.next=False
        Clear_ArgumentCount.next=False
        #EnableJump.next=False
        programmRAM_addr.next=REG_ProgramCounter+1
        #constantsRAM_addr.next=0
        
        StackOP.next=STACK_NOP
        StackOP_CMPmode.next=0
        Stack_DataIn.next=0
        
        varRAM_we.next=False
        VariablesAddr.next=0
        varRAM_din.next=StackValue0[VAR_BITWIDTH:].signed()
        
        IO_we.next=False
        IO_addr.next=0
        IO_din.next=StackValue0[VAR_BITWIDTH:].signed()
        
        StackTopSel.next=ENUM_SEL_NONE
        
        #if REG_StackTopSel==ENUM_SEL_CONST:
        #  Stack_DataIn.next=constantsRAM_dout
        if REG_StackTopSel==ENUM_SEL_GLOBAL:
          Stack_DataIn.next=IO_dout
        elif REG_StackTopSel==ENUM_SEL_VARIABLE:
          Stack_DataIn.next=varRAM_dout
        elif REG_StackTopSel==ENUM_SEL_NONE:
          Stack_DataIn.next=0
          
        argnext_store.next=FROM_NONE
        if REG_argnext_store==FROM_GLOBAL:
          VariablesAddr.next=REG_ArgumentCount-2
          varRAM_din.next=IO_dout[VAR_BITWIDTH:].signed()
          varRAM_we.next=True 
        elif REG_argnext_store==FROM_VAR:
          VariablesAddr.next=REG_ArgumentCount-2
          varRAM_din.next=varRAM_dout
          varRAM_we.next=True
        #elif REG_argnext_store==FROM_CONST:
        #  VariablesAddr.next=REG_ArgumentCount-2
        #  varRAM_din.next=constantsRAM_dout
        #  varRAM_we.next=True 
          
        if Opcode==23: #dis.opmap['BINARY_ADD']:            # 23,
            StackOP.next=STACK_ADD
        elif Opcode==64: #dis.opmap['BINARY_AND']:        # 64,
            StackOP.next=STACK_AND
        elif Opcode==62: #dis.opmap['BINARY_LSHIFT']:        #: 62,
            StackOP.next=STACK_LSHIFT
        elif Opcode==66: #dis.opmap['BINARY_OR']:        #: 66,
            StackOP.next=STACK_OR
        elif Opcode==63: #dis.opmap['BINARY_RSHIFT']:        #: 63,
            StackOP.next=STACK_RSHIFT
        elif Opcode==24: #dis.opmap['BINARY_SUBTRACT']:        #: 24,
            StackOP.next=STACK_SUB
        elif Opcode==65: #dis.opmap['BINARY_XOR']:        #: 65,
            StackOP.next=STACK_XOR
        elif Opcode==107: #dis.opmap['COMPARE_OP']:        #: 107,  
            StackOP.next=STACK_CMP
            StackOP_CMPmode.next=Arg1
        elif Opcode==4:    #dis.opmap[''DUP_TOP']: #  4
            StackOP.next=STACK_DUP_TOP
        elif Opcode==113: #dis.opmap['JUMP_ABSOLUTE'] :        #: 113,
            #EnableJump.next=True
            programmRAM_addr.next=Arg1+REG_PC_offsetValue
        elif Opcode==110: #dis.opmap['JUMP_FORWARD']:        #: 110,
            #EnableJump.next=True
            #print "JUMP_FORWARD"
            programmRAM_addr.next=REG_ProgramCounter+1+Arg1  #relative jump
        elif Opcode==111: #dis.opmap['JUMP_IF_FALSE_OR_POP']:        #: 111,
            if StackValue0[1:0]==0:
              #EnableJump.next=True
              programmRAM_addr.next=Arg1+REG_PC_offsetValue
            else:
              StackOP.next=STACK_POP
        elif Opcode==112: #dis.opmap['JUMP_IF_TRUE_OR_POP']:        #: 112,
            if StackValue0[1:0]==1:
              programmRAM_addr.next=Arg1+REG_PC_offsetValue
              #EnableJump.next=True
            else:
              StackOP.next=STACK_POP
        #elif Opcode==100: #dis.opmap['LOAD_CONST']:        #: 100,
        #    if REG_ArgumentCount==0:
        #      StackOP.next=STACK_LOAD
        #      StackTopSel.next=ENUM_SEL_CONST
        #      constantsRAM_addr.next=Arg1
        #    else:
        #      Inc_ArgumentCount.next=True
        #      constantsRAM_addr.next=Arg1
        #      argnext_store.next=FROM_CONST
        elif Opcode==124: #dis.opmap['LOAD_FAST']:        #: 124,  
            if REG_ArgumentCount==0:
              StackOP.next=STACK_LOAD
              VariablesAddr.next=Arg1
              StackTopSel.next=ENUM_SEL_VARIABLE
            else:
              Inc_ArgumentCount.next=True
              varRAM_addr_rd.next=Old_Variables_addr_offset+Arg1
              argnext_store.next=FROM_VAR
        elif Opcode==116:  #dis.opmap['LOAD_GLOBAL']: #116,
            if Arg1>=InfoRegsList[0]:
              Inc_ArgumentCount.next=True
              Set_Variables_offset.next=True
            if REG_ArgumentCount==0:  # load from global mem
              StackOP.next=STACK_LOAD
              IO_addr.next=Arg1
              StackTopSel.next=ENUM_SEL_GLOBAL
            else:
              Inc_ArgumentCount.next=True
              IO_addr.next=Arg1
              argnext_store.next=FROM_GLOBAL
              
        elif Opcode==131: #dis.opmap['CALL_FUNCTION']
            #print "############### Call Function ##########"
            Push_Programcounter.next=True
            #Enable_PC_offset.next=True
            programmRAM_addr.next=StackValue0[PROG_SIZE_BITWIDTH:]  #%CONST_PROGRAMM_LENGTH
            #print "testVAl",StackValue0[PROG_SIZE_BITWIDTH:]
            PC_offsetValue.next=StackValue0[PROG_SIZE_BITWIDTH:]    #%CONST_PROGRAMM_LENGTH  #Put on the stack with LOAD_GLOBAL 
            StackOP.next=STACK_POP
            # The Function Arguments are not loaded over the stack
            # they are written directly to the Variables RAM if the LOAD_GLOBAL argument is in the Function address range
            Clear_ArgumentCount.next=True
        elif Opcode==83: #dis.opmap['RETURN_VALUE']
            #print "############### Return Function ##########"
            #Enable_PC_offset.next=True
            PC_offsetValue.next=Old_PC_offsetValue  
            programmRAM_addr.next=Old_ProgrammCounter+1
            Pop_Programcounter.next=True
            #StackOP.next=STACK_POP_BLOCK
        elif Opcode==97: #dis.opmap['STORE_GLOBAL']: 97,
            IO_we.next=True
            IO_addr.next=Arg1
            StackOP.next=STACK_POP
        elif Opcode==114: #dis.opmap['POP_JUMP_IF_FALSE']:        #: 114,
            StackOP.next=STACK_POP
            if StackValue0[1:0]==0:
              programmRAM_addr.next=Arg1+REG_PC_offsetValue
              #EnableJump.next=True
        elif Opcode==115: #dis.opmap['POP_JUMP_IF_TRUE']:        #: 115,
            StackOP.next=STACK_POP
            if StackValue0[1:0]==1:
              programmRAM_addr.next=Arg1+REG_PC_offsetValue
              #EnableJump.next=True
        elif Opcode==1: #dis.opmap['POP_TOP']
            StackOP.next=STACK_POP
        elif Opcode==5: #dis.opmap['ROT_FOUR']:        #: 5,
            StackOP.next=STACK_ROT_FOUR
        elif Opcode==3: #dis.opmap['ROT_THREE']:        #: 3, 
            if REG_sub_pc_count==0:
              sub_pc_count_next.next=REG_sub_pc_count+1
              programmRAM_addr.next=REG_ProgramCounter
              StackOP.next=STACK_ROT_THREE_0
            if REG_sub_pc_count==1:
              sub_pc_count_next.next=0
              StackOP.next=STACK_ROT_THREE_1      
        elif Opcode==2: #dis.opmap['ROT_TWO']:        #: 2,
            StackOP.next=STACK_ROT_TWO
        elif Opcode==125: #dis.opmap['STORE_FAST']:        #: 125,
            varRAM_we.next=True   
            VariablesAddr.next=Arg1
            StackOP.next=STACK_POP
        elif Opcode==15: #dis.opmap['UNARY_INVERT']:      #:15
            StackOP.next=STACK_INVERT
        elif Opcode==11: #dis.opmap['UNARY_NEGATIVE']:        #: 11,
            StackOP.next=STACK_NEGATIVE
        elif Opcode==12: #dis.opmap['UNARY_NOT']:        #: 12,
            StackOP.next=STACK_NOT
        elif Opcode==10: #dis.opmap['UNARY_POSITIVE']:        #: 10,
            StackOP.next=STACK_POSITIVE
        elif Opcode==120: #dis.opmap['SETUP_LOOP']: # TODO?? #(explanation from python homepage) Pushes a block for a loop onto the block stack. The block spans from the current instruction with a size of delta bytes.
            StackOP.next=STACK_SETUP_LOOP
            #print "##########setup loop"
        elif Opcode==87: #dis.opmap['POP_BLOCK']:   # TODO?? dis.opmap['POP_BLOCK']
            StackOP.next=STACK_POP_BLOCK
            #print "##########pop block"
        else:
            StackOP.next=STACK_NOP
            if CpuUsesRam==False:
              programmRAM_addr.next=0 #TODO should be -1
            #raise ValueError("Unsuported Command:"+str(Opcode))
            #if rst!=0:
            print "Comand maybe not supported:",Opcode
    
    if DEBUG_OUTPUT:
      import dis
      cmp_op = dis.cmp_op
      hasconst = dis.hasconst
      hasname = dis.hasname
      hasjrel = dis.hasjrel
      haslocal = dis.haslocal
      hascompare = dis.hascompare
      @always(Opcode,Arg1)
      def monitor_opcode():
        
        instruction = (dis.opname[int(Opcode)]+" "+str(int(Opcode)), None, None, None)
        
        if Opcode in hasconst:
                instruction = (instruction[0],int(Arg1) ,'const=', CPU_CONSTANTS[int(Arg1)])
        elif Opcode in hasname:
#		#print CPU_GLOBALS
                if Arg1>=8 and (instruction[0]==dis.opmap['LOAD_GLOBAL']):
                  instruction = (instruction[0],int(Arg1) ,'global=', CPU_GLOBALS[int(Arg1)])
                else:
                  instruction = (instruction[0],int(Arg1) ,None, None)
                #print "Error: no name instruction is supported yet"
                #raise StopSimulation
        elif Opcode in hasjrel:
                instruction = (instruction[0], int(Arg1),'addr=', REG_ProgramCounter+Arg1)
        elif Opcode in haslocal:
                instruction = (instruction[0], int(Arg1),'var=', int(varRAM_dout.val))
        elif Opcode in hascompare:
                instruction = (instruction[0], int(Arg1),'cmp=', cmp_op[Arg1])
        print instruction
        
        
        
    
    if DEBUG_OUTPUT:
      return seq_logic,comb_logic,comb_logic2,VariablesRAM_inst,ProgrammCode_inst,TheStack_inst,IOModule_inst,splitOpcodeArg,muxRAMtoRS232Programmer,rs232_instance,RS232Programmer_inst,InfoREGSRAM,monitor_opcode
    else:
      return seq_logic,comb_logic,comb_logic2,VariablesRAM_inst,ProgrammCode_inst,TheStack_inst,IOModule_inst,splitOpcodeArg,muxRAMtoRS232Programmer,rs232_instance,RS232Programmer_inst,InfoREGSRAM #,monitor_opcode
    
  
def Processor_TESTBENCH():
    global CPU_BITWIDTH,CPU_CLK_FREQ
    WORD_SZ=CPU_BITWIDTH
    rst, clk = [Signal(bool(0)) for i in range(2)]
    PORTA_IN=Signal(intbv(0)[WORD_SZ:])
    PORTB_IN=Signal(intbv(0)[WORD_SZ:])
    PORTC_OUT=Signal(intbv(0)[WORD_SZ:])
    PORTD_OUT=Signal(intbv(0)[WORD_SZ:])
    iRX = Signal(bool(1))
    oTX = Signal(bool(0))
    #oTX_9 = Signal(bool(0))
    #iRX_prog = Signal(bool(1))
    #oTX_prog = Signal(bool(0))
    CpuOrProgrammerActive = Signal(bool(1))
    #toVHDL(Processor,clk,rst,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX,VAR_BITWIDTH=WORD_SZ)
    Processor_inst=Processor(clk,rst,CpuOrProgrammerActive,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX,DEBUG_OUTPUT=False)
    
    @always_comb
    def uart_loopback():
        iRX.next=oTX
    
    @always(delay(10))  
    def clkgen():
        clk.next = not clk  
        
    @instance
    def stimulus():
        print "Reseting ########"
        rst.next=0
        print "Setting PORTA_IN too 0 ########"
        PORTA_IN.next=0
        
        for i in range(3):
            yield clk.negedge
        print "Release Reset ########"
        rst.next=1
        
        for i in range(200):
            yield clk.negedge
        
        print "Setting PORTA_IN too 1 (PORTC bit 0 should toggle) ########"
        PORTA_IN.next=1
        for i in range(2000):
            yield clk.negedge
        
        print "Setting PORTA_IN too 0 (PORTC bit 0 should stop toggling) ########"
        PORTA_IN.next=0
        for i in range(1000000):
            yield clk.negedge
        
        raise StopSimulation
      
    @instance
    def Monitor_PORTC():
        print "\t\tPortC:",PORTC_OUT,"Binary:" ,bin(PORTC_OUT,WORD_SZ) ##TODO bin is not supported in simulation
        while 1:
            yield PORTC_OUT
            print "\t\tPortC:",PORTC_OUT,"Binary:" ,bin(PORTC_OUT,WORD_SZ)
        
    @instance
    def Monitor_PORTD():
        print "PortD:",PORTD_OUT
        while 1:
            yield PORTD_OUT
            print "PortD:",PORTD_OUT
            
    return clkgen,Processor_inst,stimulus,Monitor_PORTC,Monitor_PORTD,uart_loopback
    
#def ClkSysClk(clk_intern):
    
    #@always(clk_intern)
    #def logic():
        ## do nothing here
        #pass
      
    #clk_intern.driven="wire"
    
    #__vhdl__="""OSCInst0: OSCH
    #-- synthesis translate_off
    #GENERIC MAP ( NOM_FREQ => "2.08" )
    #-- synthesis translate_on
    #PORT MAP (
    #STDBY=> '0',
    #OSC=> %(clk_intern)s);"""
    
    #return logic

def pyCPU_TOP(iClk,iRst,iISP_act,oISP_selected,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX):
    global CPU_CLK_FREQ
    Clk_frequenz=CPU_CLK_FREQ
    
    ISPUsesRAM=Signal(bool(0))
    ISP_select=Signal(bool(1))

    Processor_inst=Processor(iClk,iRst,ISP_select,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX,DEBUG_OUTPUT=False)
    

    ##################key debouncer und reset logic ##############
    DebounceTime=0.05 
    DebounceCount=int(DebounceTime*Clk_frequenz)
    countclks=Signal(intbv(0,min=0,max=int(DebounceTime*Clk_frequenz)+2))
    iPushBn_synced=Signal(bool(1))
    iPushBn_synced2=Signal(bool(1))
    DebouncedKeyValue=Signal(bool(1))
    DebouncedKeyValue_delayed=Signal(bool(1))
   
    StatePress=Signal(intbv(0,min=0,max=6))
    @always(iClk.posedge,iRst.negedge)
    def key_debounce():
      if iRst==0:
        countclks.next=0
        iPushBn_synced.next=True
        iPushBn_synced2.next=True
        DebouncedKeyValue.next=True
        DebouncedKeyValue_delayed.next=True
        ISPUsesRAM.next=False
        StatePress.next=0
        #btn_rst.next=True
      else:
        countclks.next=countclks+1
        iPushBn_synced.next=iISP_act
        iPushBn_synced2.next=iPushBn_synced
        ISPUsesRAM.next=False
        #btn_rst.next=True
        if countclks==DebounceCount: # (int(DebounceTime*Clk_frequenz)+1):
          countclks.next=0
          DebouncedKeyValue.next=iPushBn_synced2
          DebouncedKeyValue_delayed.next=DebouncedKeyValue
        if StatePress==0:
          if (not DebouncedKeyValue_delayed) and (not DebouncedKeyValue):    ##button pressed
            StatePress.next=1
        elif StatePress==1:
          if (DebouncedKeyValue_delayed) and (DebouncedKeyValue):    ##button released
            StatePress.next=2
        elif StatePress==2:  
          ISPUsesRAM.next=True  
          if (not DebouncedKeyValue_delayed) and (not DebouncedKeyValue):    ##button pressed
            StatePress.next=3
        elif StatePress==3:
          ISPUsesRAM.next=True
          if (DebouncedKeyValue_delayed) and (DebouncedKeyValue):    ##button released
            StatePress.next=0
            #btn_rst.next=False ##assert the reset for one Cycle
    ##################key debouncer ##############
    
    ## invert ISP_select
    @always_comb
    def combo_logic():
      ISP_select.next=not ISPUsesRAM
      oISP_selected.next=ISPUsesRAM

    return Processor_inst,combo_logic ,key_debounce

##################### convert pico Board to VHDL###################
#NumberArguments=42
#for i in range(NumberArguments):
    #code="A"+str(i)+"= Signal(bool(0))"
    #exec(code)

#code="toVHDL(PicoBoard"
#for i in range(NumberArguments):
  #code=code+",A"+str(i)
#code=code+")"
#exec(code)

clk=Signal(bool(0))
rst=Signal(bool(0))
iISP_act=Signal(bool(0))
oISP_selected=Signal(bool(0))
PORTA_IN=Signal(intbv(0)[CPU_BITWIDTH:])
PORTB_IN=Signal(intbv(0)[CPU_BITWIDTH:])
PORTC_OUT=Signal(intbv(0)[CPU_BITWIDTH:])
PORTD_OUT=Signal(intbv(0)[CPU_BITWIDTH:])
iRX=Signal(bool(1))
oTX=Signal(bool(0))
toVHDL(pyCPU_TOP,clk,rst,iISP_act,oISP_selected,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,iRX,oTX)
##################### convert pico Board to VHDL###################

#toVHDL(Processor,clk,rst,PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT,VAR_BITWIDTH=WORD_SZ)
#toVHDL(Processor_TESTBENCH)
tb = traceSignals(Processor_TESTBENCH)
#sim = Simulation(Processor_TESTBENCH())
sim = Simulation(tb)
sim.run()    
    
    
    


#def convert():
#    WORD_SZ=8
#    DEPTH=16384
    
#    we, clk = [Signal(bool(0)) for i in range(2)]
#    dout = Signal(intbv(0)[WORD_SZ:])
#    din = Signal(intbv(0)[WORD_SZ:])
#    addr = Signal(intbv(0)[16:])
    
#    toVHDL(RAM, dout, din, addr, we,clk,WORD_SZ,DEPTH)
      
#convert()

#def simulate(timesteps):
#    tb = traceSignals(test_dffa)
#    sim = Simulation(tb)
#    sim.run(timesteps)

#simulate(20000)
