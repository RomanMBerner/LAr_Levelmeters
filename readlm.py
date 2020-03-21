#!/usr/bin/python
import sys, os

from lmclass import levelmeter

def help():
    print("Usage: ")
    print('readlm <serialport> [options]\n\n')
    print('Options:')
    print('-l dir      Local save in a directory. The file will be called \"timestamp.txt\"')
    #print('-d dburl    Send data to influx database.')
    print('-q          Quiet mode: no print out of the measurement results')
    print('-h          Show this help')
    print('\n')



#_dburl = None
_comport = None
_outdir = None
_quiet = False


if len(sys.argv)<2:
    print('Error: the serial port must be given!\n')
    help()
    sys.exit()
else:
    #Check if that file exists
    _comport = sys.argv[1]
    if not os.path.exists(_comport):
        print('Error: the serial port ' + _comport + ' does not exists')
        sys.exit()

nargs = len(sys.argv)
#Check all the arguments
iarg = 1
while iarg < nargs:
    if sys.argv[iarg] == '-h':
        help()
        sys.exit()
    if sys.argv[iarg] == '-l':
        if (iarg==(nargs-1)) or (sys.argv[iarg+1][0]=='-'):
            print('Warning: output directory not given. Ignoring the option.\n')
        else:
            _outdir = sys.argv[iarg+1]
            iarg += 1
            if not os.path.exists(_outdir):
                print('Note: output directory ' + _outdir + ' does not exists. Making it.')
                os.system('mkdir -p ' + _outdir)
            #Check for writing acces to the directory
            if not os.access(_outdir, (os.W_OK|os.X_OK|os.R_OK)):
                print('Warning: do not have right privileges to access and write in the directory ' + outdir + '\n')
                _outdir = None
        
    '''
    if sys.argv[iarg] == '-d':
        if (iarg==(nargs-1)) or (sys.argv[iarg+1][0]=='-'):
            print('Warning: influxdb url not given. Ignoring option.\n')
        else:
            _dburl = (sys.argv[iarg+1]
            iarg += 1
    '''
    if sys.argv[iarg] == '-q':
        _quiet = True
    iarg += 1


#This should be made using a json format or a configuration text file
_dbinfo = {
    'url': 'http://lhepdaq2.unibe.ch',
    'port': 8086,
    'dbname': 'mediumtube_purity_experiment_march_2020',
    'post_pF': 'lvl_pF,size=small,pos=module value=', #In the db are in the "From" column
    'post_mm': 'lvl_mm,size=small,pos=module value=',
}


lm = levelmeter(devName=_comport, dbinfo=_dbinfo, outdir=_outdir, quiet=_quiet)
#lm = levelmeter(devName=_comport, outdir=_outdir, quiet=_quiet) #This is for testing only
lm.SetSleepTime(1) #Sleep time (in seconds) after a measurement
lm.SetAverageTime(1)
lm.SetCref(150)
lm.SetBaseline(50.237)
lm.SetConvRatio(0.05)
lm.run()
