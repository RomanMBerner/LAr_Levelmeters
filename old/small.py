# //////////////////////////////////////////////// //
#                                                  //
# python3 script to read the small levelmeter      //
#                                                  //
# Last modifications: 11.01.2019 by R.Berner       //
#                                                  //
# //////////////////////////////////////////////// //

import time
import datetime
import serial
import subprocess

today = datetime.datetime.today().strftime("%d.%m.%Y")
now = datetime.datetime.now().strftime("%Y-%m-%d | %H:%M:%S")

determine_baseline = False

# Create a new file data_DATE.txt and write the header
if determine_baseline:
    headerFile = open('small_'+today+'.txt', 'a')
    headerFile.write('Date\t\tTime\t\tNumber\tcap [pF]\n')
    headerFile.close()

# Create a new file mean-of-1second_DATE.txt and write the header
#headerFile = open('mean-of-1second_'+today+'.txt', 'a') # for appending: 'a'; directory: 'c:/.../.../data.txt'
#headerFile.write('Date\t\tTime\t\tMeas.per sec.\tMean of one second [pF]\n')
#headerFile.close()

# Create a new file mean-of-5seconds_DATE.txt and write the header
#headerFile = open('mean-of-5seconds_'+today+'.txt', 'a') # for appending: 'a'; directory: 'c:/.../.../data.txt'
#headerFile.write('Date\t\tTime\t\tMeas.per 5 sec.\tMean of five seconds [pF]\n')
#headerFile.close()

# Open serial port
try:
    ser = serial.Serial(
    port = '/dev/ttyUSB0',
        baudrate = 115200,
        parity = serial.PARITY_NONE,
        bytesize = serial.EIGHTBITS,
        stopbits = serial.STOPBITS_ONE,
        timeout = 1)
    print("connected to: \t\t%r" %ser.name)
    print("connection is open: \t%r" %ser.is_open)
except IOError:
    print("IOError! Try another port number.")

ser.write('@@'.encode('utf-8')) # initialization
time.sleep(0.2)
ser.write('4'.encode('utf-8')) # select Mode 4 (3 capacitors 0 - 300 pF)
time.sleep(0.2)
ser.write('s'.encode('utf-8')) # select Mode s (slow); change to f if you want to use fast mode

c = 0.0 # remaining parasitic capacitance [pF] of the box only
baseline = 50.237 #51.2117108765 # 51.1776874463 # 52.3237953 (for the Viper_run_April_2018) # capacitance [pF] when the levelmeter is in GAr only and the temperature is ~ the operation temperature
dC_dx = 0.05 # pF/mm
#dist_bottom_top_flange = 459 # [mm]
print('Offset:\t%5.4f pF\n' %c)
print('Baseline:\t%5.4f pF\n' %baseline)

print('Type the number of measurements: (for infinity: 0)')

try:
    measurements = 0 #input()
    measurements = int(measurements)
except ValueError:
    print("Type an integer.")

counter = 0 # counter for a finite number of measurements
# number_of_measurement = 1 # counter for the number of the measurement in the raw data

second_old = datetime.datetime.now().strftime("%S")
measurements_per_second = 0
sum_1second = 0
mean_of_1second = 0
counter_5seconds = 1
measurements_per_5second = 0
sum_5seconds = 0
mean_of_5seconds = 0

while counter < measurements or measurements == 0:
    input1 = 'm' # change to: "input()" if you want to do all things manually
    converted_input = input1.encode('utf-8')

    # Send the character to the device
    ser.write(converted_input)

    # Wait max. 0.05 seconds before reading output (give device time to answer)
    time.sleep(0.05)
    while ser.inWaiting() > 1:
        output = ser.readline()
        converted_output = output.decode('utf-8')

        # Split the string into 3 pieces, part4 is empty:
        part1, part2, part3, part4 = converted_output.split(" ")

        # Translate the strings from hex to a decimal number; translation via: decnumber = int(hexnumber, 16)
        capB = int(part1, 16)
        capC = int(part2, 16)
        capD = int(part3, 16)

        cref = 150
        result = cref * (capD - capB) / (capC -capB) + c

        if (result > 500 or result < 0): continue

        #print(result)

        # Create a string with the data:
        now = datetime.datetime.now().strftime("%Y-%m-%d | %H:%M:%S.%f")
        results = str(now) + '\t' + str(round(result,6)) + '\n' # + str(number_of_measurement) + '\t'
        #print(results)

        # Save this raw data to a file
        if determine_baseline:
            saveFile = open('small_'+today+'.txt', 'a') # for appending: 'a'; directory: 'c:/.../.../data.txt'
            saveFile.write(results)
            saveFile.close()

        # Build the mean value of all raw data in one single second
        second_new = datetime.datetime.now().strftime("%S")

        if second_old == second_new:
            sum_1second = sum_1second + result
            measurements_per_second = measurements_per_second + 1
        elif second_old != second_new:
            sum_1second = sum_1second + result
            measurements_per_second = measurements_per_second + 1
            mean_of_1second = sum_1second / measurements_per_second

            #print(mean_of_1second)

            post_1s_pF = "lvl_pF,size=small,pos=module value=" + str(c+mean_of_1second-baseline)
            post_1s_mm = "lvl_mm,size=small,pos=module value=" + str((c+mean_of_1second-baseline)/dC_dx)
            #print(post_1s_pF)
            #print(baseline)
            #print(post_1s_mm)
            #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=module_zero_run_jan2019", "--data-binary", post_1s_pF])
            #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=argoncube_purity_experiment_august_2019", "--data-binary", post_1s_pF])
            subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=mediumtube_purity_experiment_march_2020", "--data-binary", post_1s_pF])
            #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=module_zero_run_jan2019", "--data-binary", post_1s_mm])
            #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=argoncube_purity_experiment_august_2019", "--data-binary", post_1s_mm])
            subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=mediumtube_purity_experiment_march_2020", "--data-binary", post_1s_mm])

            # Save data to a file
            #saveFile = open('mean-of-1second_'+today+'.txt', 'a') # for appending: 'a'; directory: 'c:/.../.../data.txt'
            #now = datetime.datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
            #result_mean_of_1second = str(now) + '\t' + str(measurements_per_second) + '\t' + str(round(mean_of_1second,6)) + '\n'
            #saveFile.write(result_mean_of_1second)
            #saveFile.close()

            # Build the mean value of 5 seconds and write it in mean-of-5seconds.txt
            #if counter_5seconds % 5 == 0: # and number_of_measurement != 1
                #mean_of_5seconds = (mean_of_5seconds + result) / 5
                #measurements_per_5second = measurements_per_5second + measurements_per_second

                #saveFile = open('mean-of-5seconds_'+today+'.txt', 'a') # for appending: 'a'; directory: 'c:/.../.../data.txt'
                #now = datetime.datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
                #result_mean_of_5second = str(now) + '\t' + str(measurements_per_5second) + '\t' + str(round(mean_of_5seconds,6)) + '\n'
                #print("----------------------")
                #print(result_mean_of_5second)
                #print("----------------------")

                #post_5s_pF = "lvl_pF,no=0,size=small,pos=module value=" + str(c+mean_of_5seconds-baseline)
                #post_5s_mm = "lvl_mm,no=0,size=small,pos=module value=" + str((c+mean_of_5seconds-baseline)/dC_dx) # - dist_bottom_top_flange)
                #print(post_5s_pF)
                #print(baseline)
                #print(post_5s_mm)

                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=slowcontrol", "--data-binary", post_5s_pF])
                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=slowcontrol", "--data-binary", post_5s_mm])
                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=resistive_shell_tpc_run_july_2018", "--data-binary", post_5s_pF])
                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=resistive_shell_tpc_run_july_2018", "--data-binary", post_5s_mm])
                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=module_zero_run_january_2019", "--data-binary", post_5s_pF])
                #subprocess.call(["curl", "-i", "-XPOST", "http://lhepdaq2.unibe.ch:8086/write?db=module_zero_run_january_2019", "--data-binary", post_5s_mm])
                #saveFile.write(result_mean_of_5second)
                #saveFile.close()

                #measurements_per_5second = 0
                #mean_of_5seconds = 0
                #counter_5seconds = 1
            #elif counter_5seconds % 5 != 0:
                #measurements_per_5second = measurements_per_5second + measurements_per_second
                #print(measurements_per_5second)
                #mean_of_5seconds = mean_of_5seconds + result
                #counter_5seconds = counter_5seconds + 1

            second_old = second_new
            measurements_per_second = 0
            sum_1second = 0

        if measurements != 0:
            counter = counter + 1

        #number_of_measurement = number_of_measurement + 1

ser.close()
