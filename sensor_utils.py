import serial
import math
import numpy as np
import time
import pandas as pd
from scipy.signal import find_peaks, chirp, peak_widths
import matplotlib.pyplot as plt

def openPort(com_port):
    try:
        serial_port = serial.Serial(com_port, timeout=0.1, writeTimeout=0.1, baudrate=115200)
        return serial_port
    except Exception as ex:
        print(f'Failed to create a serial port on port: {com_port}')
        raise ex


def closePort(serial_port):
    try:
        serial_port.close()
        print('Serial Port Successfully Closed')

    except Exception as ex:
        print('Failed to Disconnect from Serial Port')
        raise ex


def calculateCorrectionFactor(serial_port, length=300):
    # Initialize array for acceleration values used for calibration
    acc_cal = []

    # Iterate acceleration calculation to obtain calibration factor while sensor is at rest
    for i in range(0, length):
        serial_port.write(';39\n'.encode())
        read_data = serial_port.readline()
        strip_decode_data = read_data.decode().rstrip().lstrip()
        data = strip_decode_data.split(',')

        # try statement to avoid loop failure if there is an error in readline()
        # except statement gives sensor a 0.05s break to get realigned
        try:
            # Pull x, y, z acceleration values from data array
            x_acc = float(data[0])
            y_acc = float(data[1])
            z_acc = float(data[2])

        except:
            time.sleep(0.05)

        # Simple 3D acceleration calculation and append final acceleration value
        acc = np.sqrt(x_acc ** 2 + y_acc ** 2 + z_acc ** 2)
        acc_cal.append(acc)

        # Print statement to visually follow progress
        print(length - i)

    # Calibration factor helps calculate zero-acceleration for current sensor orientation
    calibration_factor = np.average(acc_cal)
    return calibration_factor


def calculateVelocity(serial_port, calibration_factor=1, acceleration_filter=0.03, length=500):
    # Initialize Arrays
    # 3 required entries to start for velocity filtering logic
    i = 3
    acceleration_array = [0, 0, 0]
    velocity_raw_array = [0, 0, 0]
    time_now = time.time_ns()
    time_array = [time_now, time_now, time_now]

    while i < length:
        # Write command to sensor; Read sensor data
        # Strip and Decode sensor output
        serial_port.write(';39\n'.encode())
        read_data = serial_port.readline()
        strip_decode_data = read_data.decode().rstrip().lstrip()
        data = strip_decode_data.split(',')

        # Pull x, y, z acceleration values from readline() data array
        try:
            x_acc = float(data[0])
            y_acc = float(data[1])
            z_acc = float(data[2])

            # Calculate total acceleration and correct for calibration factor
            acceleration_raw = np.sqrt(x_acc ** 2 + y_acc ** 2 + z_acc ** 2)
            acceleration_corrected = acceleration_raw - calibration_factor

            # Filter low acceleration values to prevent drift
            # Default acceleration filter is set at 0.03
            if abs(acceleration_corrected) < acceleration_filter:
                acceleration_filtered = 0
            else:
                acceleration_filtered = acceleration_corrected

            # Append filtered acceleration to array
            acceleration_array.append(acceleration_filtered)

            # Generate timestamp info for calculation
            t1 = time.time_ns()
            t0 = time_array[-1]
            time_delta = (t1 - t0) * 1e-9  # Convert from ns to seconds
            time_array.append(t1)

            # Integration of Acceleration
            # Logic to reset to zero-velocity to prevent drift, if needed
            if acceleration_array[-1] == 0 and acceleration_array[-2] == 0 and acceleration_array[-3] == 0:
                velocity_raw = 0
            else:
                velocity_raw = (acceleration_filtered * time_delta) + velocity_raw_array[-1]

            velocity_raw_array.append(velocity_raw)

        except:
            time.sleep(.05)

        # Print and iterate to visually follow progress
        print(length - i)
        i = i + 1

    return time_array, acceleration_array, velocity_raw_array


def findPeakVelocity(velocity_array):
    peaks, _ = find_peaks(velocity_array, distance=15, height=0.4)
    peak_width,width_height,peak_start,peak_end = peak_widths(velocity_array, peaks, rel_height=0.5)
    return peaks, peak_width


def checkBatteryPercent(serial_port):
    serial_port.write(';202\n'.encode())
    read_data = serial_port.readline()
    strip_decode_data = read_data.decode().rstrip().lstrip()
    data = strip_decode_data.split(',')
    battery = float(data[0])
    return battery


def round_up_to_even(f):
    return math.ceil(f/2.) * 2


def writeSetReport(dictionary, peaks=[],widths=[]):
    dataframe = pd.DataFrame(dictionary)
    writer = pd.ExcelWriter('Rep Report.xlsx', engine='xlsxwriter')
    book = writer.book
    #sheet_AllReps = book.add_worksheet('AllReps')
    dataframe.to_excel(writer, sheet_name='AllReps', startrow=2)


    sheet_AllReps = writer.sheets['AllReps']

    bold = book.add_format({'bold': True, 'size': 24})
    sheet_AllReps.write('A1', 'Rep Report', bold)

    chart = book.add_chart({'type': 'line'})
    end_rep = len(dataframe) + 4
    reps = len(peaks)

    chart.add_series(
        {'values': f'=AllReps!$D$4:$D${end_rep}',
         'marker': {'type': 'circle',
                    'border': {'color': 'gray'},
                    'fill': {'color': 'gray'}
                    },
         'line': {'color': 'gray'},
         'smooth': True})

    chart.set_title({'name': f'{reps}-Rep Velocity vs. Time'})
    chart.set_x_axis({'name': 'Time'})
    chart.set_y_axis({'name': 'Velocity (m/s)'})
    sheet_AllReps.insert_chart('H4', chart)

    i = 1
    for rep in range(len(peaks)):
        sheet_rep = book.add_worksheet(f'Rep {i} Data')

        peak_velocity = peaks[rep] + 4
        rep_width = round_up_to_even(widths[rep])
        rep_start = peak_velocity - (rep_width / 2)
        rep_end = peak_velocity + (rep_width / 2)

        sheet_rep.write('A1', f'Rep {i} Chart')
        chart_rep = book.add_chart({'type': 'line'})
        chart_rep.add_series(
            {'values': f'=AllReps!$D${rep_start}:$D${rep_end}',
             'marker': {'type': 'circle',
                        'border': {'color': 'gray'},
                        'fill': {'color': 'gray'}
                        },
             'line': {'color': 'gray'},
             'smooth': True})

        chart_rep.set_x_axis({'name': 'Time'})
        chart_rep.set_y_axis({'name': 'Velocity (m/s)'})
        sheet_rep.insert_chart('A2', chart_rep)

        i = i + 1

    book.close()


def basicGraph(velocity, peaks):
    plt.plot(velocity, color='grey', linestyle='-')
    for i in peaks:
        plt.plot(i, velocity[i], color='green', linestyle='dotted', markersize=12)
    plt.ylabel('Velocity (m/s)')
    plt.xlabel('Time')
    # plt.ylim([-2,2])
    plt.show()




