#!/usr/bin/env python
# Description: UART Receiver and Transmitter with Receive- and Transmitbuffer
#
# Module Signals:
# +++++++++++++++
#iClk -> Clock Signal
#iRst -> Reset Signal
#iRX  -> Receiver input Signal
#oTX  -> Transmitter output Signal
#iData -> Data to write to the transmit-buffer
#WriteEnable -> Strobe this signal to write iData to the transmit-buffer (write address is incremmented in the Module)
#oWrBuffer_full -> Indicates that the transmit-buffer is full. If Data is strobed when the transmit-buffer is indicated full it is ignored
#oData -> Output data at the read_addr of the receive-buffer. (oData<=receive-buffer[read_addr] on the next iClk clock-edge)
#read_addr -> Address to read from the receive-buffer
#oRx_addr -> Address where the next byte which will be received will be put into the receive-buffer
#Clkfrequenz -> Constant which should be set to the frequency of iClk
#Baudrate -> Constant to set the Baudrate of the unit.
#RX_BUFFER_LENGTH -> Constant, sets the receive-buffer size
#TX_BUFFER_LENGTH -> Constant, sets the transmit-buffer size
#
# Author: Norbert Feurle
# Last edit Date: 11.5.2012
# Licence: Only use it to do good, no garantie warranty

from myhdl import *

def RS232_Module(iClk,iRst,iRX,oTX, iData,WriteEnable,oWrBuffer_full,oData,read_addr,oRx_addr,Clkfrequenz=12e6,Baudrate=38400,RX_BUFFER_LENGTH=8,TX_BUFFER_LENGTH=8): 
    ##### Constants #####
    CounterCycle=int(Clkfrequenz/Baudrate)
    CounterCycle_half=int(Clkfrequenz/(Baudrate*2.0))

    ##### Signal definitions for Receiver Part ####
    Receive_RAM=[Signal(intbv(0)[8:]) for i in range(RX_BUFFER_LENGTH)]
    rx_counter=Signal(intbv(0,min=0,max=CounterCycle+2))
    rx_currentData=Signal(intbv(0)[9:])
    rx_bit_count=Signal(intbv(0,min=0,max=10))
    rx_addr=Signal(intbv(0,min=0,max=RX_BUFFER_LENGTH))
    rx_State=Signal(intbv(0,min=0,max=4))
    
    ##### Signal definitions for Transmitter Part ####
    Transmit_RAM=[Signal(intbv(0)[8:]) for i in range(TX_BUFFER_LENGTH)]
    tx_counter=Signal(intbv(0,min=0,max=CounterCycle+2))
    tx_bit_count=Signal(intbv(0,min=0,max=11))
    tx_addr=Signal(intbv(0,min=0,max=TX_BUFFER_LENGTH))
    write_addr=Signal(intbv(0,min=0,max=TX_BUFFER_LENGTH))
    tx_State=Signal(intbv(0,min=0,max=4))
    SendREG=Signal(intbv(0)[10:])
    sig_WrBuffer_full=Signal(bool(0))
    
    @always_comb
    def comb2_logic():
      oWrBuffer_full.next=sig_WrBuffer_full
      
    @always_comb
    def comb_logic():
      if ((write_addr+1)%TX_BUFFER_LENGTH)==tx_addr:
        sig_WrBuffer_full.next=True
      else:
        sig_WrBuffer_full.next=False
      
    @always(iClk.posedge,iRst.negedge)
    def seq_logic():
      if iRst==0:
        ###### Resets Receiver Part #####
        rx_State.next=0
        rx_counter.next=0
        rx_currentData.next=0
        rx_bit_count.next=0
        rx_addr.next=0
        oRx_addr.next=0

        ###### Resets Transmitter Part #####
        tx_State.next=0
        tx_addr.next=0
        write_addr.next=0
        SendREG.next=0
        tx_counter.next=0
        tx_bit_count.next=0
      else:
        oRx_addr.next=rx_addr
        oData.next=Receive_RAM[read_addr]
        oTX.next=1

        ################## Receiver Part ################
        if rx_State==0: #IDLE STATE
          if iRX==0:
            rx_counter.next=rx_counter+1
          else:
            rx_counter.next=0
          if rx_counter==CounterCycle_half:
            rx_State.next=1
            rx_counter.next=0
            rx_bit_count.next=0
            
        elif rx_State==1:  #RECEIVING STATE
          rx_counter.next=rx_counter+1
          if rx_counter==0:
            rx_currentData.next=concat(iRX,rx_currentData[9:1])
            rx_bit_count.next=rx_bit_count+1
          if rx_counter==CounterCycle:
            rx_counter.next=0
          if rx_bit_count==9:
            rx_State.next=2
            rx_counter.next=0
            
        elif rx_State==2:  #STOPBIT STATE
          rx_counter.next=rx_counter+1
          if rx_counter==CounterCycle:
            rx_State.next=0
            rx_counter.next=0
            if iRX==1: #Stopbit is Received
              Receive_RAM[rx_addr].next=rx_currentData[9:1]
              rx_addr.next=(rx_addr+1)%RX_BUFFER_LENGTH
        
        
        ################## Transmitter Part ################
        #### Writing Data to Transmit Buffer ####
        #TODO Buffer full flag#
        if WriteEnable and (not sig_WrBuffer_full):
          Transmit_RAM[write_addr].next=iData
          write_addr.next=(write_addr+1)%TX_BUFFER_LENGTH
        
        #### Transmitting Statmachine ####
        if tx_State==0:
          if write_addr!=tx_addr:
            tx_counter.next=0
            tx_State.next=1
            tx_bit_count.next=0
            SendREG.next=concat(intbv(1)[1:],Transmit_RAM[tx_addr],intbv(0)[1:])
            tx_addr.next=(tx_addr+1)%TX_BUFFER_LENGTH
        elif tx_State==1: ### Send Bytes
          oTX.next=SendREG[tx_bit_count]
          tx_counter.next=tx_counter+1
          if tx_counter==CounterCycle:
            tx_bit_count.next=tx_bit_count+1
            tx_counter.next=0
            if tx_bit_count==9:
              tx_State.next=0
        
    return seq_logic,comb_logic,comb2_logic


def test_bench():
    ###### Constnats #####
    Clk_f=12e6 #12 Mhz
    BAUDRATE=38400 
  
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
    rs232_instance=RS232_Module(iClk,iRst,iRX,oTX, iData,WriteEnable,  \
         oWrBuffer_full,oData,read_addr,rx_addr,Clkfrequenz=Clk_f,  \
         Baudrate=BAUDRATE,RX_BUFFER_LENGTH=RX_BUFF_LEN)
    
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

    def Write_to_rs232_send_buffer(value):
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

      #### wait until data is received #####
      count=0
      currentArryPos=0
      while 1:
        yield iClk.posedge
        yield delay(0)
        count=count+1
        if rx_addr!=read_addr:
          count=0
          print "RXData:", oData,"\tTXData:",testARRAY[currentArryPos], "\t\tBuffer Address:",read_addr
          assert testARRAY[currentArryPos]==oData
          currentArryPos=currentArryPos+1
          read_addr.next=(read_addr+1)%RX_BUFF_LEN

        #if Nothing is received for six possible complete RS232 transmissions
        # (8+2) means 8 Bits + 1 Startbit + 1 Stopbit
        if count>((Clk_f*1.0/BAUDRATE)*(8+2)*6):  
          if not (currentArryPos==len(testARRAY)):
            print "Warning: Not all values of the Array have been received (Check if Transmittbuffer was full)"
            print "Missing Data is:", testARRAY[currentArryPos:]
          break
    
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
      testARRAY=[0x55,0xAA,0xff,0,1,128,0xef,0xfe]
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)
      
      #### Some Test Data ####
      testARRAY=[8,4,5,2,1,0]
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)

      #### Some Test Data ####
      testARRAY=[255,254,253,251]
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)
      
      
      #### Reseting #####
      iRst.next=1
      yield delay(50)
      iRst.next=0
      yield delay(50)
      iRst.next=1
      yield delay(50)
      
      ### artificial reset of read_addr ####
      read_addr.next=0
      
      #### Some Test Data ####
      testARRAY=[0x55,0xAA,0xff,0,1,128,0xef,0xfe,8,89,55]
      print
      print "Running Test Array:",testARRAY
      print "#"*50
      yield TestTransmitReceive(testARRAY)
      
      print
      print "End of Simulation, simulation succesfull!"
      raise StopSimulation

    return  clk_gen,rs232loopback,stimulus,rs232_instance#,Monitor_oTX

if __name__ == '__main__':
  tb = traceSignals(test_bench)
  sim= Simulation(tb)
  #sim = Simulation(test_bench())
  sim.run()
