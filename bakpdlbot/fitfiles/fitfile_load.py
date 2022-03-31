import os
import datetime
from fitparse import FitFile    # https://github.com/dtcooper/python-fitparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from matplotlib.text import Annotation

ftp = None

# set up try / except loop:
n = 0
while n < 3:
    try:
        # ftp = int(input("Enter FTP in watts (whole numbers only):  "))
        ftp = 321
        print(f"\nYour FTP has been recorded as {ftp} watts.")
        break
    except ValueError:
        n += 1
        print("\nYour FTP value cannot contain letters, be left blank, or be entered as a decimal value. \n")

def load_fitfile(filename):
    """
    Load fitfile from filename and return data in dataframe format
    :param filename:
    :return: df dataframe
    """
    fitfile = FitFile(filename)

    while True:
        try:
            fitfile.messages
            break
        except KeyError:
            continue
    workout = []
    for record in fitfile.get_messages('record'):
        r = {}
        for record_data in record:
            r[record_data.name] = record_data.value
        workout.append(r)
    df = pd.DataFrame(workout)
    return df

filename = input("Type filename, including .fit extension:  ")
# filename = 'fitfile.fit'
df = load_fitfile(filename)

## Get date of workout
timestamp = df['timestamp'].tail(1).values
date = np.datetime_as_string(timestamp, unit='D')

date_str = str(date)
type(date_str)
print(date_str)

date_str = date_str.strip("[")
date_str = date_str.strip("]")
date_str = date_str.strip("'")
print(date_str)

#Remove unnecessary columns
df.columns
df_subset = pd.DataFrame(df, columns=['heart_rate', 'power', 'speed'])

#insert column time_unit
df_subset.insert(loc=0, column='time_unit', value=np.arange(len(df_subset)))

df_subset.rename(columns = {'power':'watts'}, inplace = True)

df_subset.loc[df_subset['watts'] == "NaN"]
df_subset['watts'].fillna(0, inplace=True)

# Workout .fit file recorded by Zwift?

#Give user the opportunity to enter how often .fit file data is recorded, in seconds (default is once per second, as on Zwift)
zwift_or_not = 'y' #input("Was your fit file recorded by Zwift, and/or did you device record the workout in 1-second increments?  \nEnter 'y' for yes or 'n' for no. ")

if zwift_or_not == 'y' or zwift_or_not == '':
    rec_freq = 1
    print(f"\nThe default recording frequency has been set to {rec_freq} second.")

# If .fit file not recorded by Zwift, how frequently was data recorded, in seconds?

if zwift_or_not == 'n':
    # default recording frequency to start with:
    rec_freq = 1

    # set up try / except loop:
    n = 0
    while n < 3:
        try:
            rec_freq = int(input(
                "Please enter the frequency that your workout data was recorded, in seconds.  \nEntry must be in numbers >0 and <=60, e.g., '1' for once per second, '5' to represent data recorded once every 5 seconds, '10' to signify once every 10 seconds, etc.   "))
            print(f"\nThe recording frequency has been set to {rec_freq} second(s).")
            break
        except ValueError:
            n += 1
            print()
        if n == 3:
            print(f"\nThe recording frequency has been set to {rec_freq} second(s).")

workout_data = df_subset.to_records(index=False)
watts = workout_data['watts']
max_watts = max(watts)
np.argmax(watts)

#Smooth power curve
# using helper function 'smooth.py'

watts_smoothed = watts #smooth(watts, window_len=10)

# converting recording data into minutes
# freq represents how many rows of data are contained in 1 minute of workout time
# For example, if data is recorded every 5 seconds, then there will be 12 rows of data
# per every one minute of workout time

freq = 60 / rec_freq
minutes = workout_data['time_unit']/freq

max_pwr_idx = np.argmax(workout_data['watts'])
max_pwr_timestamp = minutes[max_pwr_idx]

#Find maximum heart rate value and time stamp
hr = workout_data['heart_rate']
max_hr = max(hr)
max_hr_idx = np.argmax(workout_data['heart_rate'])
max_hr_timestamp = minutes[max_hr_idx]

if ftp != None:
    figsize = (18, 8)
    img, ax1 = plt.subplots(figsize=figsize)
    ax1.set_facecolor(color='#252525')
    ax1.set_xlabel("Time in Minutes", fontsize='large')
    ax1.set_ylabel("Watts", fontsize='large')
    ax1.tick_params(labelsize='large')

    # This expands the top of the graph to 60% beyond max watts
    ax1.set_ylim(top=max(watts) * 1.80)

    # logic for color under the graph based on % of FTP (thanks to Jonas Häggqvist for this code)
    ax1.grid(which='major', axis='y', alpha=0.1, linewidth=1)
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 0.00 * ftp, color='#646464')
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 0.60 * ftp, color='#328bff')
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 0.75 * ftp, color='#59bf59')
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 0.90 * ftp, color='#ffcc3f')
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 1.05 * ftp, color='#ff663a')
    plt.fill_between(minutes, watts_smoothed, where=watts_smoothed > 1.18 * ftp, color='#ff340c')

    # Setting workout date annotation (thanks to Phil Daws for the code that helped me get started)
    # Note:  xy for the purposes of workout date label is set using 'data' for coordinates
    xmin, xmax = ax1.get_xlim()
    ymin, ymax = ax1.get_ylim()
    xy = [xmax - (xmax * 0.05), ymax - (ymax * 0.05)]

    # Adding the workout date to the graph
    workout_date = Annotation(f'Workout date: {date_str}', xy=[xmax // 2, ymax - (ymax * 0.08)],
                              ha='center', color='white', fontweight='bold', fontsize='large')
    ax1.add_artist(workout_date)

    # Plot smoothed power, line color, and thickness
    plt.plot(minutes, watts_smoothed, color='white', linewidth=0.75)

    # Annotate max power
    max_power = Annotation(f'{max_watts}w', xy=(max_pwr_timestamp, max_watts), xytext=(0, 15),
                           textcoords="offset pixels", ha='center', color='white', fontweight='bold',
                           fontsize='large', arrowprops=dict(arrowstyle='wedge', color='yellow'))
    ax1.add_artist(max_power)

    plt.vlines(x=max_pwr_timestamp, ymin=0, ymax=max_watts, color='white', linewidth=1.5)

    # Instantiate second y axis for heart rate graph
    if (len(hr[(hr>0)]>0)):
        ax2 = ax1.twinx()
        ax2.set_ylabel("Heart Rate", fontsize='large')
        ax2.set_ylim(top=round(max(hr) * 1.30))

        # Plot heart rate
        ax2.plot(minutes, hr, color='red', linewidth=0.75)

        # Annotate max heart rate
        max_hr_annt = Annotation(f'{max_hr}bpm', xy=(max_hr_timestamp, max_hr), xytext=(0, 15),
                                 textcoords="offset pixels", ha='center', color='white', fontweight='bold',
                                 fontsize='large', arrowprops=dict(arrowstyle='wedge', color='red'))
        ax2.add_artist(max_hr_annt)
    else:
        print('no hr')

    plt.show()

else:
    print(f"\nThe graph cannot be drawn; no valid FTP was provided.")
    print(f"If you wish to try again, please have your FTP value ready and then reload this page.")
