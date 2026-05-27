"""
Python interface for atmosphere-controlled post-curing chamber
developed for vat photopolymerization research.

Functionality:
- oxygen monitoring
- humidity monitoring
- temperature monitoring
- nitrogen valve control
- live plotting
- CSV export

Developed at:
Technical University of Denmark (DTU)

Authors: Marina Artemeva, Ole Hjarvard Damgaard, Marta Barbieri 
"""

#importing necessary libraries 
# ARDUINO MUST NOT BE RUNNING OR ERROR WILL BE DISPLAYED: line 64, in open 
#  raise SerialException("could not open port {!r}: {!r}".format(self.portstr, ctypes.WinError()))
#  serial.serialutil.SerialException: could not open port 'COM3': PermissionError(13, 'Access is denied.', None, 5)

import serial       # communicating with arduino and sending commands
import time
import datetime
import struct       # used to send value to Arduino

import csv  # to print to external file

import matplotlib   #to display live plots
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import numpy as np 
import pandas as pd     # to create DataFrame and export .csv file

COM_PORT = 'COM7'   # change according to your system
BAUD_RATE = 9800

arduino = serial.Serial(port=COM_PORT, baudrate=BAUD_RATE)

time.sleep(2)       # give Arduino time to reset

start_time = datetime.datetime.now()  # start time measurement

#---------------------------------------------------------------------- fixing initial input from Arduino
arduino.reset_input_buffer()      # flush noise from Arduino reset
# Skip boot-up garbage lines
for _ in range(3):          # this range can be adjusted, there is not a specific reason of why it is set to 3 except that is works (for now)
    try:
        garbage = arduino.readline()
        #print("Skipping startup line:", garbage)
    except:
        pass
#======================= Initialize empty arrays ===========================
time_data = np.array([])
oxyg_data = np.array([])
setlevel_data = np.array([])
temp_data = np.array([])
humi_data = np.array([])

oxyg = 0  # placeholder to avoid NameError
temp = 0  # placeholder to avoid NameError
humi = 0  # placeholder to avoid NameError

#-------------------------------------------------------------- PARAMETERS FOR OXYGEN CONTROL
value = 22   # default value (also DEFINED IN ARDUINO, changing this one will do nothing) for Oxygen setlevel (overwritten when the user selects option 2: Set Oxygen Setlevel [%Vol])
# logic of oxygen control is defined in Arduino code, some parameters can be changed for a better control (see Arduino)
#--------------------------------------------------------------

#====================== Create subplots ===========================================================================
fig, (ax1,ax2,ax3) = plt.subplots(3,1, sharex = True, figsize = (14, 10), gridspec_kw = {'hspace': 0.4})

# plot 1 oxygen 
line1, = ax1.plot(time_data, oxyg_data, marker = '.', linestyle = '--', color = '#29a0b1', label = 'Oxygen [% Vol]')
line1_setlevel, = ax1.plot(time_data, setlevel_data, marker = ',', linestyle = '-.', color = '#FFAC1C', label = 'Setlevel')
ax1.set_xlabel('Time [s]')
ax1.set_ylabel('Oxygen Level [%]')
ax1.set_title('Oxygen Level Plot')
ax1.legend(loc = 'upper left')
ax1.grid(True)


# Setup plot 1 Temperature
line2, = ax2.plot(time_data, temp_data, marker = '.', linestyle = '--', color = '#29a0b1', label = 'Temperature [°C]')
ax2.set_xlabel('Time [s]')
ax2.set_ylabel('Temperature [°C]')
ax2.set_title('Temperature Plot')
ax2.legend(loc = 'upper left')
ax2.grid(True) 

# Setup plot 2 Humidity 
line3, = ax3.plot(time_data, humi_data, marker = '.', linestyle = '--', color = '#FFAC1C', label = 'Humidity [%RH]')
ax3.set_xlabel('Time [s]')
ax3.set_ylabel('Humidity Level [%RH]')
ax3.set_title('Humidity Level Plot')
ax3.legend(loc = 'upper left')
ax3.grid(True)

plt.ion()       # function allows dynamic update of plots withouth explicit commands


# =============================== Define function to export .CSV file ======================
def save_to_csv(filename):
    global time_data, oxyg_data, setlevel_data, humi_data, temp_data
    try:
        # Create DataFrame
        df = pd.DataFrame({
            'time': time_data,
            'oxygen': oxyg_data,
            'setlevel': setlevel_data,
            'temp': temp_data,
            'humidity': humi_data,
        })

        # Save DataFrame to .csv
        df.to_csv(f'{filename}.csv', index = False)
        print(f"Data saved to {filename}.csv succesfully")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

# ============================== Define function to upload plots =============================
def update_plot(frame):
    global time_data, oxyg_data, setlevel_data, humi_data, temp_data, value
    try:
        line = arduino.readline().decode("utf-8").strip()
        data = line.split()

        if len(data) != 3:  #skips data if the received from arduino is not complete
            print("Incomplete data received:", data)
            return

        oxyg = float(data[0])
        temp = float(data[2])   # temperature expressed in Celsius  
        humi = float(data[1])

        #Update arrays
        time_data = np.append(time_data, frame)
        oxyg_data = np.append(oxyg_data, oxyg)
        setlevel_data = np.append(setlevel_data, [value])
        temp_data = np.append(temp_data, temp)
        humi_data = np.append(humi_data, humi)

        #Update plots
        line1.set_data(time_data, oxyg_data)
        line1_setlevel.set_data(time_data, setlevel_data)
        ax1.relim()
        ax1.autoscale_view()

        line2.set_data(time_data, temp_data)
        ax2.relim()
        ax2.autoscale_view()

        line3.set_data(time_data, humi_data)
        ax3.relim()
        ax3.autoscale_view()

    except (ValueError, IndexError) as e:
                print("Error Parsing Line:", e)
    except UnicodeDecodeError as e:
        print("Unicode Decode Error:", e)
    except Exception as e:
        print("Error:", e)
    return line1, line1_setlevel, line2, line3

# ====================================================================================================================
# ====================================================================================================================
# =================== ENTERING MAIN LOOP OF SCRIPT (INTERFACE THROUGH TERMINAL) ======================================
# ====================================================================================================================
# ====================================================================================================================
try:
    while True:
# Print interface on terminal
        print("-----------------------------------------------------------------------------------------")
        print("-----------------------------------------------------------------------------------------")
        print("")
        print("           ENVIRONMENTAL CONTROL SETUP MENU:")
        print("")
        print("-----------------------------------------------------------------------------------------")
        print("-----------------------------------------------------------------------------------------")
        print("1: Start Fan")
        print("2: Set Oxygen Setlevel [% Vol]")
        print("3: Start Oxygen Control") 
        print("4: Start Animated Plot")
        print("5: Reset Data Acquisition")
        print("6: Display current ECS data")
        print("7: Print Data to .CSV File")
        print("8: Stop Oxygen Control") 
        print("9: Stop Fan")
        print("10: Exit Environmental Control Setup")
        print("-----------------------------------------------------------------------------------------")
        print("-----------------------------------------------------------------------------------------")

        # define different cases
        user_command = input("Enter a command from the menu: ").strip().lower()

        if user_command == "1":  # displaying current ECS data value with units (from last data acquired live [-1])
            arduino.write(b'O\n')           # in arduino O is the command that starts the fan
        elif user_command == "2":    # define oxygen level desired in chamber  (default value is set to value = 20 (see line 36))
            value = input("Enter Oxygen Setlevel value:")
            print("Oxygen Setlevel:")
            print(value)
            value = float(value)
            packed = struct.pack('f', value)
            arduino.write(b'F')
            arduino.write(packed) # sending setlevel to arduino
            input("press Enter to continue")
        elif user_command == "3":  # start oxygen control (send command to arduino) # WORKS BUT NEEDS TO BE UPDATED FOR THE ACTUAL ARDUINO SCRIPT
            arduino.write(b'H\n')
        elif user_command == "4": # animation created and updated every second
            anim = FuncAnimation(fig, update_plot, interval = 1000, cache_frame_data = False)
            plt.show()
        elif user_command =="5": # reset data acquisition
            time_data = np.array([])
            oxyg_data = np.array([])
            setlevel_data = np.array([])
            temp_data = np.array([])
            humi_data = np.array([]) 
        elif user_command == "6": # ----------------------------------------------------------------------------------------------
            print("Oxygen Setlevel [%Vol]:", setlevel_data[-1])                 
            print("Oxygen Current Level [%Vol]: ", oxyg_data[-1])
            print("Temperature [°C]:", temp_data[-1])
            print("Humidity [%RH]:", humi_data[-1])
            input("press Enter to continue")
        elif user_command == "7": #-------------------------------------------------------------------------------------------
            filename = input("Enter CSV filename (without extension):")
            save_to_csv(filename)
            print(f"Data saved to {filename}.csv")
        elif user_command == "8":   # forced stop oxygen control (send command to arduino)   # WORKS BUT NEEDS TO BE UPDATED FOR THE ACTUAL ARDUINO SCRIPT
            arduino.write(b'L\n')
        elif user_command == "9": #---------------------------------============================
            arduino.write(b'N\n')           # in arduino N is the command that stops the fan         
        elif user_command == "10": #=======================================================================================
            print("-----------------------------------------------------------------------------------------")
            print("                   EXITING PROGRAM")
            print("-----------------------------------------------------------------------------------------")
            break
        else:
            print("-----------------------------------------------------------------------------------------")
            print("")
            print("           INVALID COMMAND! SELECT INPUT FROM MENU:")
except KeyboardInterrupt:
    print("\nExiting program")
finally:
    arduino.close()