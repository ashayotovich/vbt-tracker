import sensor_utils as util
import time
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

# Connect Sensor ('COM4') via Serial Bluetooth
serial_port = util.openPort('COM4')

# Check Sensor Battery Level
# print(checkBatteryPercent(serial_port))

# Calculate Gravity Correction on Sensor, while at rest
calibration_factor = util.calculateCorrectionFactor(serial_port, length=100)
print(calibration_factor)

# Pull current time in ns - variable is used to create unique titles for each run
title_time = time.time_ns()

# Generate time, acceleration, and velocity data from the sensor for each workout set
time, acceleration, velocity = util.calculateVelocity(serial_port, calibration_factor, length=500)
# Correct the calculated velocity in g's to m/s
velocity_units = [i * 9.81 for i in velocity]

# Dictionaries
# Put data into dicitonary and df to access via CSV if needed
data_dictionary_raw = {'t': time, 'acc': acceleration, 'vf': velocity_units}
data_df = pd.DataFrame(data_dictionary_raw)
data_df.to_csv(f'sensor_data_{title_time}.csv')

# Number of Peaks is used as an input for # of Reps for a given set
peaks, widths = util.findPeakVelocity(velocity_units)
reps = len(peaks)
print(peaks)
print(widths)

# Write Report in Excel for Each Set - Commented out for now, not necessary
#util.writeSetReport(data_dictionary_raw,peaks,widths)

# Set Goal Velocity to compare each rep's velocity to
goal_velocity = 1.2

# Connect to Postgresql Database
# Create new Postgresql Table for each set
engine = create_engine('postgresql+psycopg2://postgres:admin@localhost:5432/postgres')
data_df.to_sql(f'vel_{title_time}',engine)

# Python Plotting for visual use after set is completed
# Not a necessity in production, but gives instant view of how the sensor performed during development
plt.plot(velocity_units, color='grey', linestyle='-')
for i in peaks:
    plt.plot(i, goal_velocity, marker='x', color='black', markersize=6)

    if velocity_units[i] > goal_velocity:
        plt.plot(i, velocity_units[i], marker='.', color='green', markersize=12)
    else:
        plt.plot(i, velocity_units[i], marker='^', color='red', markersize=6)

measured_velocity_legend = mlines.Line2D([],[],marker='_', color='grey', markersize=6, label='Measured Velocity')
target_velocity_legend = mlines.Line2D([],[],marker='x', color='black', markersize=6, label='Target Velocity')
successful_rep_legend = mlines.Line2D([],[],marker='.', color='green', markersize=12, label='Successful Rep')
missed_rep_legend = mlines.Line2D([],[],marker='^', color='red', markersize=6, label='Missed Rep')
plt.xlabel('Time')
plt.ylabel('Velocity (m/s)')
plt.legend(handles=[measured_velocity_legend,target_velocity_legend,successful_rep_legend,missed_rep_legend],loc=4)
plt.title(f'{reps}-Rep Velocity vs. Time')
plt.show()