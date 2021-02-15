# Sofar-Inverter-MODBUS-to-MQTT
Python scripts to interface with the Sofar Family of inverters via RS485/MODBUS USB interface and enable control via an MQTT interface

# Acknowlegements:
This code was built on the great work of:

https://github.com/greentangerine/ME3000

 AND
 
https://github.com/AndyWhittaker/HYD6000

Thank you so much for sharing your work and letting us all build on it

# Hardware Setup
Please see https://github.com/AndyWhittaker/HYD6000 for wiring information.

Ensure you wire the correct A and B polaity and that you connect the ground to a suitable surface on the inverter (such as the heatsink)

# Installation
Clone/download repository.

Edit the "sofarMQTT.py" variables to match your hardware and MQTT server settings

Run the "sofarMQTT.py" script with the following command 

     sudo python3 ./sofarMQTT.py
     
(you may need to install some packages, you can do this with "pip3 install package-name")
  
Script should be run continually in a "screen" instance it will report data to an MQTT server and accept commands

# Collecting Data
Data is found under the MQTT_TOPIC 

    e.g. "sensors/sofar/"
    
Each topic is named and the topics themselves can be changed in the "sofarMQTT.py" script

# Sending Commands
Commands should be sent in the MQTT_TOPIC + "command"

    e.g. "sensors/sofar/command"  

Valid commands are: AUTO, CHARGE, DISCHARGE, and STANDBY
(note: You need to include a value in Watts for CHARGE and DISCHARGE)

    e.g. "AUTO, 0"        - inverter to go into AUTO mode
   
    e.g. "CHARGE, 1000"   - inverter to charge battery at 1000W
