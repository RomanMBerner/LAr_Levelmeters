import sys, re, os, string, time, serial, shutil, signal, subprocess

import numpy as np


class DelayedKeyboardInterrupt(object):
    '''
    This class is used to let the file.write() finish when "ctrl+c" is pressed.
    It should be used as "with_item" inside a with statement
    It should not delay/handle other kind of exceptions
    '''
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)

    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        #logging.debug('SIGINT received. Delaying KeyboardInterrupt.')

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            self.old_handler(*self.signal_received)


class levelmeter:
    def __init__(self, devName, devBps=115200, devTimeout=1, restartCom=False, dbinfo=None, outdir=None, quiet=False, avtime=None):
        
        self.lastEpoch = int(0)
        self.outfilename = ''
        self.serPort = None
        self.attemCommMax = 3
        
        self.devName = str(devName)
        self.baudrate = devBps
        self.timeout = devTimeout
        self.initialized = False
        
        self.dbinfo = dbinfo
        self.outdir = outdir
        if self.outdir:
            if not self.outdir[-1]=='/':
                self.outdir += '/'
        
        self.sleeptime = 2
        self.fileLenght = None
        self.outfile = None
        self.avaragetime = avtime #Measurement average time
        
        self.measures = np.zeros(10000) #Preallocate memory. Will build the averages with this array
        
        self.baseline = 0.0
        self.dc_dx = 1.0
        self.cap_ref = 155. #Reference capacitance (given in pF)
        
        self.quiet = quiet
        
        try:
            if not self.quiet:
                print('\nTry to initialize the port "' + self.devName +'"\n')
            self.serPort = serial.Serial(self.devName, self.baudrate, timeout=self.timeout)
        except serial.SerialException as err:
            print 'Error: failed to open the serial port:\n-> Error({0}): {1}\n'.format(err.errno, err.strerror)
            #raise
            sys.exit(err)
        
        if not self.quiet:
            print('Serial port initialised.\n')
        
        time.sleep(1)
        
        self.StartComm()
    
    def StartComm(self):
        if not self.serPort.isOpen():
            if not self.quiet:
                print('Serial port found closed. Try to open it...\n')
            try:
                self.serPort.open()
            except serial.SerialException as err:
                print('\nError: failed to open the serial port:\n-> Error({0}): {1}\n')
                raise
            if not self.quiet:
                print('Serial port opened.\n')
        
        if not self.quiet:
            print('Start communication with the UTI....')
        try:
            self.serPort.write('@')
            time.sleep(0.1)
            self.serPort.write('h')
        
        except serial.SerialException as err:
            print('\nError: failed to write to the serial port:\n-> Error({0}): {1}\n'.format(err.errno, err.strerror))
            #Clear what ever is left in the output buffer
            self.serPort.flushOutput()
            self.serPort.flushInput()
            #raise
            sys.exit(err)
        except Exception as err:
            print('\nError: failed to write to the serial port:\n-> Unknown error\n')
            #Clear what ever is left in the output buffer
            self.serPort.flushOutput()
            self.serPort.flushInput()
            #raise
            sys.exit(err)
        time.sleep(0.1)
        
        if self.serPort.inWaiting()>0:
            self.initialized = True
            self.serPort.flushInput()
            if not self.quiet:
                print('communication established.\n')
            #Set the working mode of the UTI
            if not self.quiet:
                print('Setting the UTI in working mode 4 and slow reading....\n')
            try:
                self.serPort.write('s')
                self.serPort.write('4') #write 4 (mode 4, 3 cap 0-300pF);
            except serial.SerialException as err:
                #Clear what ever is left in the output buffer
                self.serPort.flushInput()
                self.serPort.flushOutput()
                print '\nError: failed to write to the serial port:\n-> Error({0}): {1}\n'.format(err.errno, err.strerror)
                #raise
                sys.exit(err)
            except Exception as err:
                #Clear what ever is left in the buffers
                self.serPort.flushInput()
                self.serPort.flushOutput()
                print '\nError: failed to write to the serial port:\n-> Unknown error\n'
                print err
                #raise
                sys.exit(err)
            time.sleep(2)
            if not self.quiet:
                print 'done.'
        else:
            self.initialized = False
            self.serPort.flushInput()
            self.serPort.flushOutput()
            if not self.quiet:
                print 'failed.\n'
    
    def resetUTI(self):
        if not self.quiet:
            print '\nResetting the UTI board:'
        
        self.initialized = False
        if self.serPort.isOpen():
            if not self.quiet:
                print '  Switch off the RTS line.... '
            self.serPort.setRTS(False)
            if not self.quiet:
                print '  done.\n'
            if not self.quiet:
                print '  Closing the serial port.... '
            self.serPort.close()
            if not self.quiet:
                print '  done.\n'
        
        if not self.quiet:
            print ' The serial port is closed. Waiting 10 seconds before re-opening and switch the UTI board on.'
        time.sleep(10)
        
        try:
            if not self.quiet:
                print '\n  Try to initialize the port "' + self.devName +'"....\n'
            self.serPort = serial.Serial(self.devName, self.baudrate, timeout=self.timeout)
        except serial.SerialException as err:
            print '\nError: failed to open the serial port:\n-> Error({0}): {1}\n'.format(err.errno, err.strerror)
            #raise
            sys.exit(err)
        except:
            print '\nError: failed to open the serial port:\n-> Unknown error\n'
            #raise
            sys.exit(err)
        print('done.\n')
        
        if not self.quiet:
            print('  Switching on the RTS line.... ')
        self.serPort.setRTS(True)
        if not self.quiet:
            print('done.')
        
        self.StartComm()
    
    
    #This is for debugging (command line)
    def getserialport(self):
        return self.serPort
    
    
    #Make it ready to used in a thread (only little modification are necessary)
    def run(self, filelenght=int(3600*1)):#By default make logfile 1 hour long
        
        if(not self.initialized):
            sys.exit('\nError: The level meter cannot be read as the class is not properly initialized! Exiting.')
        
        self.fileLenght = filelenght
        
        #start the reading cycle
        while True:
            if self.outdir:
                lastEpoch = int(time.time()) #Used to make the name of the outputfile and to check when to make a new one
                if not os.path.exists('/tmp/levelmeters'):
                    os.system('mkdir -p /tmp/levelmeters')
                try:
                    self.outfile = open('/tmp/levelmeters/'+str(lastEpoch)+'.txt','w')
                    try:
                        with self.outfile:
                            while int(time.time())<lastEpoch+filelenght:
                                self.readcycle()
                                time.sleep(self.sleeptime)
                        if os.access('/tmp/levelmeters/'+str(lastEpoch)+'.txt', (os.W_OK|os.R_OK)):
                            os.system('mv /tmp/levelmeters/'+str(lastEpoch)+'.txt ' + self.outdir)
                    except KeyboardInterrupt:
                        if self.outfile and (not self.outfile.closed):
                            self.outfile.close()
                        shutil.move('/tmp/levelmeters/'+str(lastEpoch)+'.txt', self.outdir)
                        raise
                except IOError as err:
                    print('Error: Could not open file ' + '/tmp/levelmeters/' +str(lastEpoch)+ '.txt\n-> Error({0}): {1}'.format(err.errno, err.strerror))
                    print('The data will be read without saving it to a file')
                    #Check if the file was created and in case delete it
                    self.outfile = None
                    if os.path.exists('/tmp/levelmeters/'+str(lastEpoch)+'.txt'):
                        os.remove('/tmp/levelmeters/'+str(lastEpoch)+'.txt')
            else:
                self.readcycle()
                time.sleep(self.sleeptime)
            
    
    def read(self):#Old interface (backward compatibility)
        self.readcycle()
    
    def readcycle(self):
        #Cycle until the UTI gives a good reading
        attemComm = 0 #Attempts to restart the communication
        attemRestart = False
        iVal = 0
        unixtime_0 = int(0)
        measuredone = False
        self.serPort.flushInput()
        self.serPort.flushOutput()
        while not measuredone:
            try:
                self.serPort.write('m') #single mesurement
                time.sleep(0.1)
                
                try:
                    reply = self.serPort.readline().strip()
                    unixtime = int(time.time())
                    if iVal == 0:
                        unixtime_0 = unixtime
                    
                    #The answer is made by 3 groups of 6 exadecimal digits separated from a shift each
                    matches = re.match(r'^[0-9A-F]{6} [0-9A-F]{6} [0-9A-F]{6}', reply)
                    if matches:
                        caps = map(lambda x: int(x, 16), reply.split(' '))
                        #print caps
                        if caps[1] != caps[0]:
                            val_raw = float(caps[2]-caps[0])/float(caps[1]-caps[0])
                            val = val_raw*self.cap_ref
                            meascap = val
                            if not self.avaragetime:
                                measuredone = True
                            else:
                                if (iVal == 0) or (unixtime<=unixtime_0+self.avaragetime):
                                    if iVal<len(self.measures):
                                        self.measures[iVal] = val
                                    else:
                                        self.measures.append(val)
                                    iVal += 1
                                else:
                                    measuredone = True
                            
                            if measuredone:
                                if self.avaragetime:
                                    meascap = self.measures[:iVal].mean()
                                lev = self.convert(meascap)
                                if not self.quiet:
                                    print('\nTimestamp: ' + str(unixtime))
                                    print('Capacitance: ' + str(meascap) + ' pF')
                                    print('Calibrated level: ' + str(lev) + ' cm')
                                
                                if self.outfile:
                                    #This should protect from keyboard interruption while writing the line
                                    with DelayedKeyboardInterrupt():
                                        self.outfile.write( str(unixtime) + '\t' + str(caps[0]) + '\t' + str(caps[1]) + '\t' + str(caps[2]) + '\t' + str(meascap) + '\t' + str(lev) + '\n' )
                                    
                                if self.dbinfo:
                                    self.writedbmsg(meascap, lev)
                                
                        else:
                            if not self.quiet:
                                print('Denominator zero -> capacitance not calculable!')
                            self.serPort.flushOutput()
                        #The UTI answered so reset this two variables
                        attemComm = 0
                        attemRestart = False
                    else: #The reply did not match with the expected format: checking why and make more attempts
                        self.serPort.flushInput()
                        self.serPort.flushOutput()
                        if len(reply) == 0: #In this case the serial communication might be broken
                            if attemComm < self.attemCommMax:
                                attemComm += 1
                                print('\nWarning: Empty reply! Try to restart the communication: attempt ' + str(attemComm) + '\n')
                                self.StartComm()
                            else:
                                if not attemRestart:
                                    attemRestart = True
                                    print('\nWarning: Empty reply for ' + str(attemComm) + ' times! Last attempt trying to reset the UTI board and the communication.\n')
                                    self.resetUTI()
                                else:
                                    print('\nWarning: The restart of the UTI board didn\'t work. The serial communication channel might be broken. Manual fixing is required!\n')
                                    return
                            
                        else:
                            # empty the buffer of whatever might be left
                            print('Warning: The reply doesn\'t match with the format... retry')
                            #The UTI answered so reset this two variables
                            attemComm = 0
                            attemRestart = False
                            #time.sleep(2)
                
                except serial.SerialException as err:
                    print('Error in reading the serial port -> Error({0}): {1}'.format(err.errno, err.strerror))
                    self.serPort.flushInput()
                except serial.SerialTimeoutException:
                    print('Error in reading the serial port -> Timeout')
                    self.serPort.flushInput()
                #finally:
                    #time.sleep(2)
                    
            except serial.SerialException as err:
                print('\nError: failed to write to the serial port the character "m" for the single measurement request.')
                if self.serPort.isOpen():
                    self.serPort.close()
                sys.exit(err)
        
        #Clean the buffers before exiting
        self.serPort.flushInput()
        self.serPort.flushOutput()
    
    def SetAverageTime(self, avtime):
        '''
        Setting the average time the level is averaged over.
        The time is in number of seconds.
        '''
        self.avaragetime = avtime
        
    def SetBaseline(self, bsln):
        '''Set the baseline of the capacitance measurement in pF'''
        self.baseline = bsln
        
    def SetCref(self, cref):
        self.cap_ref = cref
    
    def SetConvRatio(self, dc_dx):
        self.dc_dx = dc_dx
    
    def SetSleepTime(self, slt):
        self.sleeptime = slt
    
    def convert(self,cap):
        '''
        This function converts the capacitance in pF to liquid level in mm
        '''
        return (cap-self.baseline)/self.dc_dx
    
    
    def writedbmsg(self, cap, lev):
        '''Writes and sends the measurement to the influxdb using the informations set at the start'''
        
        premessage = self.dbinfo['url']+':'+str(self.dbinfo['port'])+'/write?db='+self.dbinfo['dbname']
        
        post_pF = self.dbinfo['post_pF'] + str(cap)
        subprocess.call(["curl", "-i", "-XPOST", premessage, "--data-binary", post_pF])
        
        post_mm = self.dbinfo['post_mm'] + str(lev)
        subprocess.call(["curl", "-i", "-XPOST", premessage, "--data-binary", post_mm])
    