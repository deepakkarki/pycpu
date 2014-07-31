from myhdl import *
import RS232_Norbo


t_State = enum('IDLE','READ_INFO_DATA', 'INFO_DATA_HERE','WAIT_ONE_CLK', 'RECEIVE_IT')
def RS232Programmer(clk,rst,enable,oInfobyte,dout,addr_out,we, \
		    iData_RS232,WriteEnable_RS232, oWrBuffer_full_RS232,oData_RS232,read_addr_RS232,rx_addr_RS232):
    
    
    ######RS232 Module#########
    ##### Signal definitions #####
    #iData_RS232=Signal(intbv(0)[8:])
    #oData_RS232=Signal(intbv(0)[8:])
    #WriteEnable_RS232=Signal(bool(0))
    #oWrBuffer_full_RS232=Signal(bool(0))
    #read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    RX_BUFF_LEN=read_addr_RS232.max
    #reg_read_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    #rx_addr_RS232=Signal(intbv(0,min=0,max=RX_BUFF_LEN))
    #oTX=Signal(bool(0))
    
        
    state=Signal(t_State.IDLE)
    Info_byte=Signal(intbv(0x09)[8:])
    countbytesRX=Signal(intbv(0)[9:])
    isData=Signal(bool(0))
    
    subcount=Signal(intbv(0,min=0,max=4))
    SUBCOUNT_MAX=subcount.max
    received_addr=Signal(intbv(0)[32:])
    received_data=Signal(intbv(0)[32:])

    @always_comb
    def data_and_addr():
      dout.next=received_data
      addr_out.next=received_addr
      oInfobyte.next=Info_byte
    
    
    @always(clk.posedge,rst.negedge)
    def IO_write_sync():
      if rst==0:
         state.next=t_State.IDLE
         read_addr_RS232.next=0
         Info_byte.next=0x09
         subcount.next=0
         isData.next=False
         countbytesRX.next=0
         WriteEnable_RS232.next=False
         iData_RS232.next=0
         we.next=False
      else:
	 WriteEnable_RS232.next=False
	 if we:
	   received_data.next=0
	   received_addr.next=0
	   countbytesRX.next=countbytesRX+1
	   iData_RS232.next=countbytesRX
	   WriteEnable_RS232.next=True
	   
	 we.next=False
	 
         if state==t_State.IDLE:
	   isData.next=False
	   if rx_addr_RS232!=read_addr_RS232:
	     read_addr_RS232.next=(read_addr_RS232+1)%RX_BUFF_LEN
	     state.next=t_State.READ_INFO_DATA
	     #print "######STate was IDLE######"
	 elif state==t_State.READ_INFO_DATA:
	   if (oData_RS232[6:3]==0) or (oData_RS232[3:0]==0):
	     Info_byte.next=0x09
	   else:
	     Info_byte.next=oData_RS232
	     #print "info RS232:", bin(oData_RS232)
	     state.next=t_State.INFO_DATA_HERE
	 elif state==t_State.INFO_DATA_HERE:
	   if rx_addr_RS232!=read_addr_RS232:
	      state.next=t_State.RECEIVE_IT
           if countbytesRX==256:
	      state.next=t_State.IDLE
	      countbytesRX.next=0
	      print "alll 256 Datas received"
	 elif state==t_State.WAIT_ONE_CLK:
	   state.next=t_State.RECEIVE_IT
	 
	 elif state==t_State.RECEIVE_IT:
	   subcount.next=(subcount+1)%SUBCOUNT_MAX  
	   if isData:
	     received_data.next=(received_data<<8)|oData_RS232
	     if (subcount+1)>=Info_byte[6:3]:
		 isData.next=False
		 subcount.next=0
		 we.next=True
	   else:
	     received_addr.next=(received_addr<<8)|oData_RS232
	     if (subcount+1)>=Info_byte[3:]:
		 isData.next=True
		 subcount.next=0
	 
	   
	   read_addr_RS232.next=(read_addr_RS232+1)%RX_BUFF_LEN
	   state.next=t_State.INFO_DATA_HERE
	
	 
	 if not enable:
	    state.next=t_State.IDLE
	    read_addr_RS232.next=rx_addr_RS232
	 
    return IO_write_sync,data_and_addr

    
def test_bench():
    ###### Constnats #####
    Clk_f=12e6 #12 Mhz
    BAUDRATE=230400
  
    ##### Signal definitions #####
    iData=Signal(intbv(0)[8:])
    oData=Signal(intbv(0)[8:])
    iClk=Signal(bool(0))
    iRst=Signal(bool(1))
    iRX=Signal(bool(1))
    oTX=Signal(bool(0))
    WriteEnable=Signal(bool(0))
    oWrBuffer_full=Signal(bool(0))
    read_addr=Signal(intbv(0,min=0,max=8))
    RX_BUFF_LEN=8
    rx_addr=Signal(intbv(0,min=0,max=RX_BUFF_LEN))

    ##### Instanziate RS232 Module #####
    rs232_instance=RS232_Norbo.RS232_Module(iClk,iRst,iRX,oTX, iData,WriteEnable,  \
         oWrBuffer_full,oData,read_addr,rx_addr,Clkfrequenz=Clk_f,  \
         Baudrate=BAUDRATE,RX_BUFFER_LENGTH=RX_BUFF_LEN,TX_BUFFER_LENGTH=RX_BUFF_LEN)
    
    
    dout=Signal(intbv(0)[32:])
    addr_out=Signal(intbv(0)[32:])
    we=Signal(bool(0))
    oTX_programmer=Signal(bool(0))
    oInfobyte=Signal(intbv(0)[8:])
    #programmer_inst=RS232Programmer(iClk,iRst,oInfobyte,dout,addr_out,we, oTX,oTX_programmer, BAUDRATE=BAUDRATE,RX_BUFF_LEN=RX_BUFF_LEN,TX_BUFF_LEN=RX_BUFF_LEN,Clk_f=Clk_f)
    
    
    oprog_Data_RS232=Signal(intbv(0)[8:])
    oprog_WriteEnable_RS232=Signal(bool(0))
    iprog_WrBuffer_full_RS232=Signal(bool(0))
    programmer_enable=Signal(bool(1))
    
    programmer_inst=RS232Programmer(iClk,iRst,programmer_enable,oInfobyte, \
                       dout,addr_out,we, \
                       oprog_Data_RS232,oprog_WriteEnable_RS232, iprog_WrBuffer_full_RS232,oData,read_addr,rx_addr)
    
    
    #toVHDL(RS232Programmer,iClk,iRst,oInfobyte,dout,addr_out,we, oTX,oTX_programmer, BAUDRATE=BAUDRATE,RX_BUFF_LEN=RX_BUFF_LEN,TX_BUFF_LEN=RX_BUFF_LEN,Clk_f=Clk_f)
    
    ##### Convert to VHDL ######
    #toVHDL(RS232_Module,iClk,iRst,iRX,oTX, iData,WriteEnable, \
    #       oWrBuffer_full,oData,read_addr,rx_addr,Clkfrequenz=Clk_f,  \
    #       Baudrate=BAUDRATE,RX_BUFFER_LENGTH=RX_BUFF_LEN)
    
    interval = delay(10)
    @always(interval)
    def clk_gen():
      iClk.next=not iClk
    
    @always_comb
    def rs232loopback():
        iRX.next=oTX

    @instance
    def Monitor():
        #print "\t\tPortC:",PORTC_OUT,"Binary:" ,bin(PORTC_OUT,WORD_SZ) ##TODO bin is not supported in simulation
        while 1:
            yield we
            if we:
	      yield delay(0)
	      print "Data:\t",bin(dout),dout,"Addr:\t",addr_out
   
    @instance
    def Monitor2():
      #### wait until data is received #####
      count=0
      currentPos=0
      while 1:
        yield iClk.posedge
        yield delay(0)
        count=count+1
        if rx_addr!=read_addr:
          count=0
          #print "RXData:", oData, "\t\tBuffer Address:",read_addr
          #assert oData==currentPos
          if currentPos==255:
	    currentPos=0
	  else:
	    currentPos=currentPos+1
          #read_addr.next=(read_addr+1)%RX_BUFF_LEN

        #if Nothing is received for six possible complete RS232 transmissions
        # (8+2) means 8 Bits + 1 Startbit + 1 Stopbit
        if count>((Clk_f*1.0/BAUDRATE)*(8+2)*10):  
          break

    def Write_to_rs232_send_buffer(value):
      yield iClk.posedge
      while oWrBuffer_full:
	yield iClk.posedge
      iData.next=value
      if oWrBuffer_full:
        print "Value:",value,"\tNot written, RS232 Transmittbuffer has indiciated to be allready full. (by oWrBuffer_full)"
      
      WriteEnable.next=1
      yield iClk.posedge
      WriteEnable.next=0
    
    def TestTransmitReceive(testARRAY):
      #### Write some Bytes to the Sendbuffer #####
      for data in testARRAY:
        yield Write_to_rs232_send_buffer(data)
      
      for i in range(int(Clk_f/BAUDRATE)*10*(RX_BUFF_LEN+3)):
	yield iClk.posedge
    @instance
    def stimulus():
      #### Reseting #####
      iRst.next=1
      yield delay(50)
      iRst.next=0
      yield delay(50)
      iRst.next=1
      yield delay(50)
      
      #### Some Test Data ####
      testARRAY=[0x09]+range(256)+range(256)+[0x12]+range(256)+range(256)+range(256)+range(256) 
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)
      

      
      #### Reseting #####
      print "Assert the reset"
      iRst.next=1
      yield delay(50)
      iRst.next=0
      yield delay(50)
      iRst.next=1
      yield delay(50)
      
      ### artificial reset of read_addr ####
      read_addr.next=0
      
      #### Some Test Data ####
      testARRAY=[0x09]+range(256)+range(256)+[0x09]+range(256)+range(256)
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)
      
      print
      print "End of Simulation, simulation done!"
      raise StopSimulation

    return  clk_gen,Monitor,stimulus,rs232_instance,programmer_inst,rs232loopback,Monitor2#,Monitor_oTX    

if __name__=='__main__':
    sim = Simulation(test_bench())
    #sim = Simulation(tb)
    sim.run()         
