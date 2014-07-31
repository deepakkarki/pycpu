import dis
import math
################# Reworking the bytecode, so that it better fits into the Processor (e.g Alignment issues)###################
class MakeBytecode:
  def __init__(self,mainfunction,PredefinedIOAddresses,OtherGlobals,ARGUMENT_BITLENGTH):
    for Portname in PredefinedIOAddresses.keys():
      OtherGlobals[Portname]=0
    Unworked_functionArray={mainfunction.func_name:mainfunction}
    occuring_globals_dict=PredefinedIOAddresses.copy()
    Processed_functions_dict={}
    function_names_inorder=[]
    Function_offset=0
    programm_dict={}
    while len(Unworked_functionArray)>0:
      funcname,currentfunction=Unworked_functionArray.popitem()
      Processed_functions_dict[funcname]=(Function_offset,currentfunction)  #create function mapping in Programm Rom (start addresses of functions)
      function_names_inorder.append(funcname)
      
      theprogramm=tuple([ord(i) for i in currentfunction.func_code.co_code]) #
      
      count=0
      new_count=0
      REWORKED_GLOBAL_PROGRAMM_OPCODE=[]
      REWORKED_GLOBAL_PROGRAMM_ARG=[]
      Addressmap_old_new={}
      
      # create a seperate opcode and argument List (fits better in myhdl ram)
      # extend opcodes without argument with an 0 argument
      while 1:
        if count<len(theprogramm):
          REWORKED_GLOBAL_PROGRAMM_OPCODE.append(theprogramm[count])
          Addressmap_old_new[count]=new_count
          if theprogramm[count]>=dis.HAVE_ARGUMENT:
            actual_Argument=(theprogramm[count+2]<<8)+theprogramm[count+1]
            REWORKED_GLOBAL_PROGRAMM_ARG.append(actual_Argument)
            if theprogramm[count]==dis.opmap['LOAD_GLOBAL']:
              if hasattr(OtherGlobals[currentfunction.func_code.co_names[actual_Argument]], '__call__'): # if GLOBAL_LOAD loads a function
                if not Processed_functions_dict.has_key(currentfunction.func_code.co_names[actual_Argument]): #if function is allready processed
                  ##every function is just added once because it is a dictionary
                  Unworked_functionArray[currentfunction.func_code.co_names[actual_Argument]]=OtherGlobals[currentfunction.func_code.co_names[actual_Argument]]
            count=count+3
          else:
            REWORKED_GLOBAL_PROGRAMM_ARG.append(0)
            count=count+1
          new_count=new_count+1
        else:
          break
      Function_offset=Function_offset+len(REWORKED_GLOBAL_PROGRAMM_OPCODE)  # next function will get next free Programm ROM Address
      # Readjust all absolute jump addresses
      for index,i in enumerate(REWORKED_GLOBAL_PROGRAMM_OPCODE):
          if i in dis.hasjabs:
            REWORKED_GLOBAL_PROGRAMM_ARG[index]=Addressmap_old_new[REWORKED_GLOBAL_PROGRAMM_ARG[index]]

      # Readjust relative jump addresses, for now only JUMP_FORWARD is changed
      count=0
      while 1:
        if count<len(theprogramm):
          if theprogramm[count]>=dis.HAVE_ARGUMENT:
            actual_Argument=(theprogramm[count+2]<<8)+theprogramm[count+1]
            if theprogramm[count]==dis.opmap['JUMP_FORWARD']:
              #print count
              REWORKED_GLOBAL_PROGRAMM_ARG[Addressmap_old_new[count]]=Addressmap_old_new[count+3+actual_Argument]-Addressmap_old_new[count+3]
            count=count+3
          else:
            count=count+1
        else:
          break
      programm_dict[funcname]=(REWORKED_GLOBAL_PROGRAMM_OPCODE,REWORKED_GLOBAL_PROGRAMM_ARG)
      ## after this: Every Opcode and argument is at one address, Absolut jumps are corrected, and relative JUMP_FORWARD is corrected  
    ########## end while len(Unworked_functionArray)>0: #########  
    
    #occuring_globals_dict=PREDEFINED_IO_ADDRESSES
    self.GLOBALS_MEM_CONTENT=[]
    if len(occuring_globals_dict)>0:
      globals_addr=max(occuring_globals_dict.values())+1
    else:
      globals_addr=0
      
    occuring_const_values_dict={}
    #self.CONSTANTS_MEM_CONTENT=[]
    if len(occuring_const_values_dict)>0:
      const_addr=max(occuring_const_values_dict.values())+1
    else:
      const_addr=0
    ### Adjust and merge LOAD_GLOBAL, STORE_GLOBAL,LOAD_CONST , and Global_mem

    ##create shared GLOBALS_MEM_CONTENT and shared CONSTANTS_MEM_CONTENT
    ###merge constants  (because python creates uniqe constants for every function)
    ###merge globals (introduce global_var_mem, only for function calling and global constants)
    ###rework global addresses (LOAD_GLOBAL, STORE_GLOBAL)
    ###rework const addresses (LOAD_CONST)
    ###rework absolut jump addresses of functions (LOAD_GLOBAL)
    ###only constant arguments are supported, or dual ported var mem is needed
    list_Load_global_when_fcall=[]
    for funcname in function_names_inorder:
      currentprogramm_opcodes=programm_dict[funcname][0]
      currentprogramm_arg=programm_dict[funcname][1]
      for index,i in enumerate(currentprogramm_opcodes[:]):
        
        if i==dis.opmap['LOAD_GLOBAL'] or i==dis.opmap['STORE_GLOBAL']:
          global_name=Processed_functions_dict[funcname][1].func_code.co_names[currentprogramm_arg[index]]
          if type(OtherGlobals[global_name])==type(0):  ##needs to be an integer 
            if not occuring_globals_dict.has_key(global_name):
              occuring_globals_dict[global_name]=globals_addr
              self.GLOBALS_MEM_CONTENT.append(OtherGlobals[global_name])
              globals_addr=globals_addr+1
            currentprogramm_arg[index]=occuring_globals_dict[global_name]
          elif i==dis.opmap['LOAD_GLOBAL'] and  hasattr(OtherGlobals[global_name], '__call__'):
            list_Load_global_when_fcall.append((funcname,global_name,index))
          else:
            print "Error: Only integers are suportted, Type is:",type(OtherGlobals[global_name])
            
        if i==dis.opmap['LOAD_CONST']:
          const_value=Processed_functions_dict[funcname][1].func_code.co_consts[currentprogramm_arg[index]]
          if type(const_value)==type(0):
            if not occuring_const_values_dict.has_key(const_value):
              self.GLOBALS_MEM_CONTENT.append(const_value)
              occuring_const_values_dict[const_value]=globals_addr
              globals_addr=globals_addr+1
            currentprogramm_arg[index]=occuring_const_values_dict[const_value]
            currentprogramm_opcodes[index]=dis.opmap['LOAD_GLOBAL']
            
          elif type(const_value)==type(None) and currentprogramm_arg[index]==0:  
          ## if no return value is defined in a function it returns a None in python but pyCpu would return what is at addres 0 in const memory
            currentprogramm_opcodes[index]=dis.opmap['LOAD_GLOBAL']
          else:
            print "Error: Only integers are suportted, Type is:",type(const_value)
      #print "------------------------------------"
      #for i in range(len(currentprogramm_opcodes)):
#	print currentprogramm_opcodes[i],currentprogramm_arg[i]
      
      #store changes
      programm_dict[funcname]=(currentprogramm_opcodes,currentprogramm_arg)
      #print occuring_globals_dict
      #print "ops:",currentprogramm_opcodes
      #print "args:",currentprogramm_arg
      
    self.GLOBAL_FUNCTION_ADRESSES_START=globals_addr
    ##### rework LOAD_GLOBAL arguments when functions are loaded and add the function address to the GLOBALS_MEM_CONTENT
    ##### functions addresses are the highest addresses in the GLOBAL_MEM,GLOBAL_FUNCTION_ADRESSES_START is used in the core
    ##### to decide wheter it is a normal LOAD_GLOBAL or if the LOAD global loads a function
    for basefuncname,callfunctionname,index in list_Load_global_when_fcall:
      if not occuring_globals_dict.has_key(callfunctionname):
        occuring_globals_dict[callfunctionname]=globals_addr
        self.GLOBALS_MEM_CONTENT.append(Processed_functions_dict[callfunctionname][0])  ### add the offset address of the function, to the GLOBAL memory
        globals_addr=globals_addr+1
      programm_dict[basefuncname][1][index]=occuring_globals_dict[callfunctionname]
            #currentprogramm_arg[index]=occuring_globals_dict[func_name]
      
    #### stitch programms of the induvidual functions together
    self.COMPLETE_PROGRAMM_OPCODES=[]
    self.COMPLETE_PROGRAMM_ARGS=[]
    for FuncName in function_names_inorder:
      self.COMPLETE_PROGRAMM_OPCODES.extend(programm_dict[FuncName][0])
      self.COMPLETE_PROGRAMM_ARGS.extend(programm_dict[FuncName][1])
    
    self.GLOBAL_STACK_SIZE=0
    for offset,func_object in Processed_functions_dict.itervalues():
      self.GLOBAL_STACK_SIZE=max(func_object.func_code.co_stacksize,self.GLOBAL_STACK_SIZE)
    
    #####set SETUP_LOOP argument to 0
    for index, opcode in enumerate(self.COMPLETE_PROGRAMM_OPCODES):
      if opcode==dis.opmap['SETUP_LOOP']:
	self.COMPLETE_PROGRAMM_ARGS[index]=0
    
    ## myhdl only works with tuples
    self.GLOBAL_STACK_SIZE=self.GLOBAL_STACK_SIZE
    if len(self.GLOBALS_MEM_CONTENT)==0:
      self.GLOBALS_MEM_CONTENT=(0,)  #needs to be a tuple of integers
    else:
      self.GLOBALS_MEM_CONTENT=tuple(self.GLOBALS_MEM_CONTENT)
    #self.CONSTANTS_MEM_CONTENT=tuple(self.CONSTANTS_MEM_CONTENT)
    self.COMPLETE_PROGRAMM_OPCODES=tuple(self.COMPLETE_PROGRAMM_OPCODES)
    self.COMPLETE_PROGRAMM_ARGS=tuple(self.COMPLETE_PROGRAMM_ARGS)
    self.GLOBAL_OPCODE_ARG_MAX_VALUE=max(self.COMPLETE_PROGRAMM_ARGS)
    
    
    assert (int(math.log(max(self.COMPLETE_PROGRAMM_ARGS),2))+1)<=ARGUMENT_BITLENGTH

    self.THE_PROGRAM=[]
    for index,opcode in enumerate(self.COMPLETE_PROGRAMM_OPCODES):
      self.THE_PROGRAM.append((opcode<<ARGUMENT_BITLENGTH)+self.COMPLETE_PROGRAMM_ARGS[index])

    self.THE_PROGRAM=tuple(self.THE_PROGRAM)
    
#####end class MakeProzesserByteCode #####################
    