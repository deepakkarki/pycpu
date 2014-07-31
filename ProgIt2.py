import os
import imp
import math
import MakeProcessorBytecode
import sys
import serial

############ configs (defined by the hardware implementation) ###################
#PREDEFINED_IO_ADDRESSES={'PORTA_IN':0,'PORTB_IN':1,'PORTC_OUT':2,'PORTD_OUT':3, \
#'RS232Data':4,'RS232_READ_ADDRESS':5,'RS232_RECEIVE_ADDRESS':6,'RS232_WRITEBUFFER_FULL':7}  #need to start at 0
#
#Prog_mem_SIZE=1024
#Var_mem_SIZE=128
#Globals_mem_SIZE=128
#
#STACK_SIZE=4
#CPU_BITWIDTH=8
#CPU_RS232_BAUDRATE=115200
############ configs (defined by the hardware implementation) ###################

def ProgrammPyCpu(Mainfile="main.py",SerDev="/dev/ttyUSB1"):
    
  #print Mainfile
  
  ### load module from a filename
  DDk=imp.load_source(os.path.splitext(Mainfile)[0],os.path.expanduser(Mainfile))

  ### empty function definition (for type checking) ####
  def kkkt():pass

  ##### create a dictionary from module Variables #########
  MD=dict([(i,getattr(DDk,i)) for i in dir(DDk) if not i.startswith('_') ]) 
  
  ### assert that the Variable PYCPU_CONFIGS is defined correctly  ####
  assert MD.has_key("PYCPU_CONFIGS"), "Error, Variable PYCPU_CONFIGS must be defined"
  assert type(MD["PYCPU_CONFIGS"]) is type({}), "Error, Variable PYCPU_CONFIGS must be a dictionary"
  assert MD["PYCPU_CONFIGS"].has_key("PREDEFINED_IO_ADDRESSES")
  assert MD["PYCPU_CONFIGS"].has_key("Prog_mem_SIZE")
  assert MD["PYCPU_CONFIGS"].has_key("Var_mem_SIZE") 
  assert MD["PYCPU_CONFIGS"].has_key("Globals_mem_SIZE") 
  assert MD["PYCPU_CONFIGS"].has_key("STACK_SIZE") 
  assert MD["PYCPU_CONFIGS"].has_key("CPU_BITWIDTH") 
  assert MD["PYCPU_CONFIGS"].has_key("CPU_RS232_BAUDRATE") 
  #len(MD["PYCPU_CONFIGS"])==7, "Error , PYCPU_CONFIGS must contain all settings" 

  
  ######All config-strings are loaded into this environment as a real variable
  for i in MD["PYCPU_CONFIGS"]:
    exec(i+"="+MD["PYCPU_CONFIGS"][i].__repr__())  
  
  

  GLOBAL_MEM_START=max(PREDEFINED_IO_ADDRESSES.values())+1

  assert CPU_RS232_BAUDRATE in serial.baudrate_constants.keys(), "Error, Baudrate is not supported"
  Baudrate_const=CPU_RS232_BAUDRATE
  
  
  ### assert that the code in the file/module has a main function ####
  assert MD.has_key("main"), "Error: Prozessor Code has no main function defined"
  assert type(MD["main"])==type(kkkt), "Error: Prozessor Code has no main function defined"


  #print Prog_mem_SIZE


  ### Make the data to be written into the pyCpu core ####
  ARGUMENT_BITLENGTH=int(math.log(Prog_mem_SIZE-1,2)+1)
  #print ARGUMENT_BITLENGTH
  ProcessorCodeObject=MakeProcessorBytecode.MakeBytecode(MD["main"],PREDEFINED_IO_ADDRESSES,MD,ARGUMENT_BITLENGTH)



  GLOBAL_FUNCTION_ADRESSES_START=ProcessorCodeObject.GLOBAL_FUNCTION_ADRESSES_START
  GLOBALS_MEM_CONTENT=ProcessorCodeObject.GLOBALS_MEM_CONTENT
  THE_PROGRAM=ProcessorCodeObject.THE_PROGRAM
  GLOBAL_STACK_SIZE=ProcessorCodeObject.GLOBAL_STACK_SIZE  ### get max stacksize


  print "Programm:",THE_PROGRAM, len(THE_PROGRAM)
  print "Globals:", GLOBALS_MEM_CONTENT
  print "Functions start in global mem at:", GLOBAL_FUNCTION_ADRESSES_START
  print "Stack size:",GLOBAL_STACK_SIZE

  
  
  assert GLOBAL_STACK_SIZE<=STACK_SIZE , "Error, The Stack_size of your programm exceeds the stacksize of the your implementation" 
  assert len(THE_PROGRAM)<=Prog_mem_SIZE, "Error, Your programm is too large for your current implementation"
  #assert len(CONSTANTS_MEM_CONTENT)<=Constants_mem_SIZE
  assert len(GLOBALS_MEM_CONTENT)<=Globals_mem_SIZE, "Error, Global memory of your implemntation is to small"
  
  
  
  info_prog_addr=1+int(math.log(max(1,Prog_mem_SIZE-1))/math.log(2**8))
  info_prog_data=1+int(math.log((2**(8+ARGUMENT_BITLENGTH))-1)/math.log(2**8))
  
  #info_const_addr=1+int(math.log(max(1,len(CONSTANTS_MEM_CONTENT)-1))/math.log(2**8))
  #info_const_data=1+int((CPU_BITWIDTH-1)/8)
  
  info_global_addr=1+int(math.log(max(1,len(GLOBALS_MEM_CONTENT)-1))/math.log(2**8))
  info_global_data=1+int((max(int(math.log(Prog_mem_SIZE-1,2))+1,CPU_BITWIDTH)-1)/8)
  
  info_REGS_addr=1
  info_REGS_data=1+int((CPU_BITWIDTH-1)/8)
  
  
  Infobyte_PROGRAM=(0<<6)|   (info_prog_data<<3)  | info_prog_addr
  #Infobyte_CONSTANTS=(1<<6)| (info_const_data<<3)   | info_const_addr
  Infobyte_GLOBALS=(2<<6)|  (info_global_data<<3)   | info_global_addr
  Infobyte_REGS=(3<<6)|   (info_REGS_data<<3)  | info_REGS_addr
  
  
  Memory=[[THE_PROGRAM,range(len(THE_PROGRAM)),Infobyte_PROGRAM],[GLOBALS_MEM_CONTENT,range(GLOBAL_MEM_START,GLOBAL_MEM_START+len(GLOBALS_MEM_CONTENT)),Infobyte_GLOBALS],[(GLOBAL_FUNCTION_ADRESSES_START,GLOBAL_STACK_SIZE),[0,1],Infobyte_REGS]]
  
  
  
  ser1=serial.Serial(SerDev)
  ser1.baudrate=Baudrate_const
  ser1.setTimeout(1)
  
  for Data,Addr,Info_byte in Memory:
    addr_bytes=Info_byte&0x07
    addr_bytes_list=range(addr_bytes)
    addr_bytes_list.reverse()
    data_bytes=(Info_byte&0x38)>>3
    data_bytes_list=range(data_bytes)
    data_bytes_list.reverse()
    
    
    
    last_index=0
    
    for index,current_data in enumerate(Data):
      if (index%256)==0:
        ser1.write(chr(Info_byte))
        print "Infobyte written:",bin(Info_byte)
      
      for i in addr_bytes_list:
	data_addr=(Addr[index]>>(8*i))&0xff
	ser1.write(chr(data_addr))
	#print "addr:",data_addr,i
      for i in data_bytes_list:
	data_current=(Data[index]>>(8*i))&0xff
	ser1.write(chr(data_current))
	#print "data:",data_current,i  
      last_index=index
      ser1.read(1)
      #print ord(ser1.read(1))
    print "#"*50
    print Data,Addr,Info_byte,addr_bytes_list,data_bytes_list
    print "#"*50
    
    ####fill up so that there are 256 writen Datas, this makes the hardware implementation simplier!
    running_index=last_index
    while (running_index%256)!=255:
      for i in addr_bytes_list:
	ser1.write(chr((Addr[last_index]>>(8*i))&0xff))
      for i in data_bytes_list:
	ser1.write(chr((Data[last_index]>>(8*i))&0xff))
      running_index=running_index+1
      #print ord(ser1.read(1))
    
    #print "#"*50
    
  ser1.close()
  
  
  
  
if __name__=="__main__":
  
  if len(sys.argv)>1:
    Mainfile=sys.argv[1] #"main.py"
  else:
    Mainfile="main.py"

  ProgrammPyCpu(Mainfile=Mainfile,SerDev="/dev/ttyUSB1")