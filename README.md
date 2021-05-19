# vbt-tracker

The 'sensor_utils.py' file contains all of the needed functions to control the sensor. Functions include connecting the sensor via bluetooth (serial), calibrating the sensor for gravity bias in its current orientation, calculating velocity over a set number of iterations, and finding the peak velocity of each rep.

The 'run_sensor.py' file is what actually calls the 'sensor_util.py' functions in a logical order to measure movement data. This file also includes some plotting functions to help the developer visualize the data right after the set is complete. This file currently commits the final dataframe to the postgres database 'postgres' as a new table.

.png file included as an example velocity graph that was generated from the 'run_sensor.py' file
