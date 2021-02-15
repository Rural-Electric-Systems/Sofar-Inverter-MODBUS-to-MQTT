#!/usr/bin/env python
import json
import serial
import time
import numpy
import paho.mqtt.client as mqtt
import signal
import sys
import gc
from time import sleep
from me3000 import ME3000

# This code was built on the great work of:
#       https://github.com/greentangerine/ME3000
#       AND
#       https://github.com/AndyWhittaker/HYD6000
#       
#       Thank you so much for sharing your work and letting us all build on it

# Script should be run continually in a "screen" instance it will report data to an MQTT server and accept commands
#   Commands should be sent in the MQTT_TOPIC + "command"
#   e.g. "sensors/sofar/command"
#   
#   Valid commands are: AUTO, CHARGE, DISCHARGE, and STANDBY
#   You need to include a value in Watts for CHARGE and DISCHARGE
#   e.g. "AUTO, 0"        - inverter to go into AUTO mode
#   e.g. "CHARGE, 1000"   - inverter to charge battery at 1000W

# SET these Variables to match your USB interface and MQTT config
MQTTServer = "127.0.0.1"
MQTTPort = 1883
MQTT_USER = "sofar"
MQTT_PWD = "sofar"
MQTT_TOPIC = "sensors/sofar/"

SLAVE=0x01 # Slave Address of Inverter
THRESHOLD=99
SERIAL_PORT="/dev/ttyUSB2" # Check this for your USB device
MIN_CHARGE=20
MAX_CHARGE=100

# Toptics can be added or removed
# Topic formats: (<location>, <name>, <h-signed/H-unsigned>, <conversion factor>)
TOPICS = ((1, 'running_state', 'H', 0.1),
          (6, 'grid_a_voltage', 'H', 0.1),
		  (7, 'grid_a_current', 'h', 0.01),
          #(8, 'grid_b_voltage', 'H', 0.1),
		  #(9, 'grid_b_current', 'h', 0.01),
          #(10, 'grid_c_voltage', 'H', 0.1),
		  #(11, 'grid_c_current', 'h', 0.01),
          (12, 'grid_frequency', 'H', 0.01),
		  (13, 'batt_power', 'h', 10), 
		  (14, 'batt_voltage', 'H', 0.1),
		  (15, 'batt_current', 'h', 0.01),
		  (16, 'batt_soc', 'H',1),
		  (17, 'batt_temp', 'H',1),
          (18, 'grid_power', 'h',10),
          (19, 'home_load_power', 'h',10),
          (20, 'inverter_power', 'h',10),
          (21, 'pv_generation_power', 'h',10),
          (22, 'eps_voltage', 'H', 0.1),
		  (23, 'eps_power', 'H', 10),
          (24, 'day_pv_generated', 'H', 0.01),
		  (25, 'day_export_grid', 'H', 0.01),
		  (26, 'day_import_grid', 'H', 0.01),
		  (27, 'day_load_use', 'H', 0.01),
          (28, 'total_pv_gen_HB', 'H', 0xffff),
          (29, 'total_pv_gen_LB', 'H', 1),
          (30, 'total_export_grid_HB', 'H', 0xffff),
          (31, 'total_export_grid_LB', 'H', 1),
          (32, 'total_import_grid_HB', 'H', 0xffff),
          (33, 'total_import_grid_LB', 'H', 1),
          (34, 'total_load_use_HB', 'H', 0xffff),
          (35, 'total_load_use_LB', 'H', 1),
		  (36, 'charge_total', 'H', 0.1),
          (37, 'discharge_total', 'H', 0.1),
          (38, 'value_38_0x226', 'H', 1),
          (39, 'value_39_0x227', 'H', 1),
          (40, 'value_40_0x228', 'H', 1),
          (41, 'value_41_0x229', 'H', 1),
          (42, 'value_42_0x22A', 'H', 1),
          (43, 'value_43_0x22B', 'H', 1),
          (44, 'batt_cycles', 'H', 1),
          (45, 'inverter_bus_voltage', 'H', 0.1),
          (46, 'llc_bus_voltage', 'H', 0.1),
          (47, 'buck_current', 'H', 0.01), #check this, Manual says Uint
          (48, 'grid_r_voltage', 'H', 0.1),
		  (49, 'grid_r_current', 'h', 0.01),
          #(50, 'grid_s_voltage', 'H', 0.1),
		  #(51, 'grid_s_current', 'h', 0.01),
          #(52, 'grid_t_voltage', 'H', 0.1),
		  #(53, 'grid_t_current', 'h', 0.01),
          (54, 'pv_generation_current_0x236', 'H',1),
          (55, 'battery_power_0x237', 'H',1),
          (56, 'inverter_internal_temp', 'h',1), #0x238
          (57, 'inverter_heatsink_temp', 'h',1),
          (58, 'country', 'H',1), #0x23A
          (59, 'dc_current', 'h',0.001), #0x23B
          (60, 'dc_voltage', 'h',0.1), #0x23C
          (61, 'batt_fault_1_61_0x23D', 'H',1), #0x23D
          (62, 'batt_fault_2_62_0x23E', 'H',1), #0x23E
          (63, 'batt_fault_3_63_0x23F', 'H',1), #0x23F
          (64, 'batt_fault_4_64_0x240', 'H',1), #0x240
          (65, 'batt_fault_1_65_0x241', 'H',1), #0x241
          (66, 'today_gen_time', 'H', 1),
          (67, 'total_gen_time_HB', 'H', 0xffff),
          (68, 'total_gen_time_LB', 'H', 1)
		 )

def on_connect(client, userdata, flags, rc):
	print("Connected with result code "+str(rc))
    # Here we subscribe to the command topic
	client.subscribe( MQTT_TOPIC + "command")

mqttcommand= ""
# This picks up the command topic values and passes to the while loop
def on_message(client, userdata, msg):
	global mqttcommand
	msg.payload = msg.payload.decode("utf-8")
	print("\n MQTT Command of Topic: "+msg.topic+ " recieved with payload: "+str(msg.payload))
	mqttcommand = str(msg.payload)
	sleep(1)
	
# Create MQTT Client
client = mqtt.Client()
# Link Callbacks with the above functions
client.on_connect = on_connect
client.on_message = on_message
# Set the username and password for MQTT here if it is needed
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.connect(MQTTServer,MQTTPort,30)
client.loop_start()

def signal_handler(signal,frame):
	print("Cleaning Up then Shutting Down")
	client.loop_stop()
	sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)

mqttcounts=0
serErrorCount = 0
inverter = ME3000(SERIAL_PORT, SLAVE)

while serErrorCount != 11:
    try:
        print("Read Data "+ str(mqttcounts))
        status, me3000_response = inverter.read_holding()
        if status != True:
            print("Read failed")
            
        mqttcounts = mqttcounts +1
        serErrorCount = 0
        print(me3000_response)
    except:
        serErrorCount = serErrorCount + 1
        wait = serErrorCount * 10
        print("Unable to read Data From Inverter, wait " + str(wait) +"s for retry. Error count: " + str( serErrorCount))
        sleep(10)
    
    if serErrorCount == 0:
        try:
            print("Publish to MQTT "+ str(mqttcounts))
            for topic in TOPICS:
                t_value = me3000_response[topic[0]]
                if topic[2] == 'h': # using struct.pack format
                    t_value = numpy.int16(t_value) # convert to signed
                t_value = int(t_value) # ensure int - need this for some reason
                t_converted = t_value * topic[3] # Multiply by conversion factor in topic
                t_topic = MQTT_TOPIC + topic[1] # build topic name
                ret = client.publish(t_topic, t_converted)
                if ret[0] != 0:
                    print("Publish failed for" + t_topic)
        except:
            print("\n Error Occured in MQTT Publish")

    if mqttcommand != "":
        mqttcommand = mqttcommand.split(", ")
        if mqttcommand[0] == "AUTO":
            print("set to Auto Mode")
            status, me3000_response = inverter.set_auto()  
        elif mqttcommand[0] == "CHARGE":
            print("set to Charge Mode")
            power = int(mqttcommand[1])
            status, me3000_response = inverter.set_charge( power )
        elif mqttcommand[0] == "DISCHARGE":
            print("set to Discharge Mode")
            power = int(mqttcommand[1])
            status, me3000_response = inverter.set_discharge( power )
        elif mqttcommand[0] == "STANDBY":
            print("set to Standby Mode")
            status, me3000_response = inverter.set_standby()
        else:
            print("\n MQTT Command not recognised")
        
        if status != True:
            print("Changing State Failed")
            
        mqttcommand = ""

    gc.collect()

    if serErrorCount == 10:
            print("max serial errors reached, exiting")		

    sleep(5)
	

client.loop_stop()
