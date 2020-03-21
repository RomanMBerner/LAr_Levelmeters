# LAr_Levelmeters
To readout the levelmeters designed to work in LAr

Need to install pyserial:
//sudo apt-get install python-serial
sudo apt-get install python3-serial

Furthermore, the USB port needs rights to read/write.
You can permanently change this with:
sudo gedit /etc/udev/rules.d/50-ttyusb.rules
KERNEL=="ttyUSB[0-9]*",NAME="tts/USB%n",SYMLINK+="%k",GROUP="uucp",MODE="0666"
Note that setting the permission to 666 allows anybody to write to the device.

First plug in the USB cable of the small LM (should be assigned to ttyUSB0), then the USB cable of the medium LM (should be assigned to ttyUSB1).
