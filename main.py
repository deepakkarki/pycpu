#################### pyCPU example Programm #########################
# Description: This simple Programm for the python Hardware Processor
#      toogles the Pin (PORTD_OUT[4]) all time long with a busy waiting
#      inbetween.
#      The Pin (PORTC_OUT[3] ) is only toggled if PORTA_IN[0]==1
#
# Date:10.2.2013
#####################################################################


PYCPU_CONFIGS={ 
  "PREDEFINED_IO_ADDRESSES":{'PORTA_IN':0,'PORTB_IN':1,'PORTC_OUT':2,'PORTD_OUT':3,'RS232Data':4,'RS232_READ_ADDRESS':5,'RS232_RECEIVE_ADDRESS':6,'RS232_WRITEBUFFER_FULL':7}, 
  "Prog_mem_SIZE":1024,          # Spezifies the minimal programm length, the programm memory will have this lenght even if the current programm dont needs it  
  "Var_mem_SIZE":128,            # Size of the Memory for local variables 
  "Globals_mem_SIZE":128,        # Size of Global memory + constants memory + PREDEFINED_IO_ADDRESSES
  "STACK_SIZE":4,                # Minimal Size of one local Stackblock, that the cpu implements, even if the programm needs less stack
  "CPU_BITWIDTH":8,              # Bitwidth of integer values
  "CPU_CLK_FREQ":12e6,           # Needed to for RS232 Baudrate calc
  "CPU_RS232_BAUDRATE":115200,   # Baudrate of the RS232 Unit 
  "NR_FUNCTION_ARGUMENTS":8,     # Limits the maximal number of arguments in a function call
  "NR_NESTED_LOOPS":32           # Limits the maximal number of nested Loops
}

#for real hardware with 12mhz clk-frequenz e.g for blinking a LED
def wait(time):
  x=0
  while x<100:
    td=0
    x=x+1
    while td<100:
      td=td+1
      ss=0
      while ss<time:
        ss=ss+1
        
#for speedy simulation        
#def wait():  # for simulation, the other wait takes too long, but for a blinking led on the Hardware its ok
  #pass
        
def main():
  global PORTA_IN,PORTB_IN,PORTC_OUT,PORTD_OUT
  PORTD_OUT=0
  PORTC_OUT=0
  while 1:
    PORTD_OUT=PORTD_OUT^16
    wait(80)
    if (PORTA_IN & 0x01)==1:
      PORTC_OUT=PORTC_OUT^8 #|0x20
    else:
      PORTC_OUT=PORTC_OUT&0xdf