from flask import Flask, send_file
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import io
import datetime
import threading
import time
import gc
import os
import math

# testing webhook (delete this line)


# Configure matplotlib to use a memory-efficient backend
matplotlib.use('Agg')

app = Flask(__name__)

# Global variables to store cached data
class DataCache:
    def __init__(self):
        self.scan_counts = None
        self.last_update = None
        self.lock = threading.Lock()

cache = DataCache()

def update_counts_csv():
    """Update counts CSV with new data."""
    try:
        counts_csv_path = 'counts.csv'
        ble_log_path = 'ble_log.csv'

        # Initialize counts_df
        if os.path.exists(counts_csv_path):
            counts_df = pd.read_csv(counts_csv_path, parse_dates=['Timestamp'])
            # Check if timestamps are timezone-naive before localizing
            if counts_df['Timestamp'].dt.tz is None:
                counts_df['Timestamp'] = counts_df['Timestamp'].dt.tz_localize('UTC')
        else:
            counts_df = pd.DataFrame(columns=['Timestamp', 'Count'])

        # Determine the last processed timestamp
        if not counts_df.empty:
            last_processed_time = counts_df['Timestamp'].max()
        else:
            last_processed_time = None

        # Read new data from ble_log.csv
        if os.path.exists(ble_log_path):
            if last_processed_time:
                # Read only new data
                new_data = pd.read_csv(ble_log_path, usecols=['Timestamp'], parse_dates=['Timestamp'])
                # Check if timestamps are timezone-naive before localizing
                if new_data['Timestamp'].dt.tz is None:
                    new_data['Timestamp'] = new_data['Timestamp'].dt.tz_localize('UTC')
                new_data = new_data[new_data['Timestamp'] > last_processed_time]
            else:
                # First run, read entire file
                new_data = pd.read_csv(ble_log_path, usecols=['Timestamp'], parse_dates=['Timestamp'])
                # Check if timestamps are timezone-naive before localizing
                if new_data['Timestamp'].dt.tz is None:
                    new_data['Timestamp'] = new_data['Timestamp'].dt.tz_localize('UTC')
        else:
            new_data = pd.DataFrame(columns=['Timestamp'])

        if not new_data.empty:
            # Drop rows with NaT values
            new_data = new_data.dropna(subset=['Timestamp'])

            # Round timestamps to the nearest minute
            new_data['Timestamp'] = new_data['Timestamp'].dt.floor('T')

            # Aggregate counts per minute
            new_counts = new_data.groupby('Timestamp').size().reset_index(name='Count')

            # Append new counts to counts_df
            counts_df = pd.concat([counts_df, new_counts], ignore_index=True)

            # Aggregate counts_df by Timestamp to handle duplicates
            counts_df = counts_df.groupby('Timestamp', as_index=False)['Count'].sum()

            # Remove data older than 48 hours
            now = pd.Timestamp.now(tz='UTC')
            last_48_hours = now - pd.Timedelta(hours=48)
            counts_df = counts_df[counts_df['Timestamp'] >= last_48_hours]

            # Sort counts_df by Timestamp
            counts_df.sort_values('Timestamp', inplace=True)

            # Save updated counts_df
            counts_df.to_csv(counts_csv_path, index=False)
        else:
            # No new data; remove old data beyond 48 hours
            now = pd.Timestamp.now(tz='UTC')
            last_48_hours = now - pd.Timedelta(hours=48)
            counts_df = counts_df[counts_df['Timestamp'] >= last_48_hours]
            counts_df.to_csv(counts_csv_path, index=False)

        return counts_df

    except Exception as e:
        print(f"Error updating counts CSV: {e}")
        return None

def update_data():
    """Function to update the cached data."""
    while True:
        try:
            counts_df = update_counts_csv()

            if counts_df is not None and not counts_df.empty:
                # Round timestamps to the nearest minute
                counts_df['Timestamp'] = counts_df['Timestamp'].dt.floor('T')

                # Aggregate counts by Timestamp to handle duplicates
                counts_df = counts_df.groupby('Timestamp', as_index=False)['Count'].sum()

                # Set Timestamp as index
                counts_df.set_index('Timestamp', inplace=True)

                # Ensure index is a DatetimeIndex and timezone-aware
                counts_df.index = pd.to_datetime(counts_df.index)
                counts_df.index = counts_df.index.tz_convert('UTC')

                # Keep only data from the last 48 hours
                now = pd.Timestamp.now(tz='UTC')
                last_48_hours = now - pd.Timedelta(hours=48)
                counts_df = counts_df[counts_df.index >= last_48_hours]

                # Apply 15-minute rolling average with centered window
                smoothed_counts = counts_df['Count'].rolling('15T', center=True, min_periods=1).mean()

                # Apply additional exponential smoothing to reduce spikes
                smoothed_counts = smoothed_counts.ewm(span=5).mean()

                # Convert to float64 to ensure proper numerical handling
                smoothed_counts = smoothed_counts.astype('float64')

                # Divide by 4 and round up after smoothing
                smoothed_counts = smoothed_counts.apply(lambda x: math.floor(x / 2) if pd.notnull(x) else x)

                # Debugging output
                print(f"Data range: min={smoothed_counts.min()}, max={smoothed_counts.max()}")

                with cache.lock:
                    cache.scan_counts = smoothed_counts
                    cache.last_update = datetime.datetime.now(datetime.timezone.utc)
                    print(f"Data updated at {cache.last_update}")

            else:
                # If counts_df is empty, create an empty smoothed_counts series
                smoothed_counts = pd.Series(dtype='float64')

                with cache.lock:
                    cache.scan_counts = smoothed_counts
                    cache.last_update = datetime.datetime.now(datetime.timezone.utc)
                    print(f"Data updated at {cache.last_update} (no new data)")

            gc.collect()

        except Exception as e:
            print(f"Error updating data: {e}")

        time.sleep(600)  # 10 minute update interval

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Living Room Occupancy Estimate</title>
        <meta http-equiv="refresh" content="600">
        <style>
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
            }
            body { 
                font-family: Arial, sans-serif; 
                background-color: #1a1a1a;
                color: #ffffff;
            }
            .container { 
                width: 100%;
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            .content {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            img { 
                flex: 1;
                width: 90%;
                object-fit: contain;
                background-color: #1a1a1a;
            }
            .status { 
                color: #999; 
                font-size: 0.9em; 
                margin: 10px; 
            }
            h1 {
                font-size: 36px;
                margin: 15px;
                color: #ffffff;
                font-weight: 600;
            }
            .subtitle {
                color: #999;
                margin: 0 15px 25px 15px;
                font-size: 18px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="content">
                <h1>How many people are in the living room?</h1>
                <p class="subtitle">15-minute average of bluetooth device count</p>
                <img src="/chart" alt="Living Room Occupancy">
            </div>
            <p class="status">Page auto-refreshes every 10 minutes</p>
            <p id="last-update" class="status"></p>
        </div>
        <script>
            function updateTimestamp() {
                fetch('/last_update')
                    .then(response => response.text())
                    .then(timestamp => {
                        document.getElementById('last-update').textContent = 
                            'Last data update: ' + timestamp;
                    });
            }
            updateTimestamp();
            setInterval(updateTimestamp, 60000);
        </script>
    </body>
    </html>
    """

@app.route('/last_update')
def last_update():
    if cache.last_update:
        return cache.last_update.strftime('%Y-%m-%d %H:%M:%S UTC')
    return 'No updates yet'

@app.route('/chart')
def chart():
    with cache.lock:
        if cache.scan_counts is None or cache.scan_counts.empty:
            return "Data not yet loaded", 503

        scan_counts = cache.scan_counts

    try:
        # Print debug info
        print(f"Plotting data with shape: {scan_counts.shape}")
        print(f"Data range: min={scan_counts.min()}, max={scan_counts.max()}")

        # Set dark mode style for matplotlib
        plt.style.use('dark_background')

        # Create figure with two subplots stacked vertically
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6.4),
                                        dpi=100,
                                        facecolor='#1a1a1a',
                                        height_ratios=[1, 1])

        # Get current time and date boundaries
        now = pd.Timestamp.now(tz='UTC')
        today_start = now.normalize()  # Start of today
        yesterday_start = (today_start - pd.Timedelta(days=1)).normalize()  # Start of yesterday (midnight)
        tomorrow_start = (today_start + pd.Timedelta(days=1)).normalize()  # Start of tomorrow (midnight)

        # Split data into yesterday and today
        yesterday_data = scan_counts[
            (scan_counts.index >= yesterday_start) &
            (scan_counts.index < today_start)
        ]
        today_data = scan_counts[
            (scan_counts.index >= today_start) &
            (scan_counts.index < tomorrow_start)
        ]

        # Function to style and plot data on an axis
        def style_subplot(ax, data, label, show_x_labels=True):
            ax.set_facecolor('#1a1a1a')

            # Plot filled area
            ax.fill_between(data.index, data.values,
                            alpha=0.2, color='#60a5fa')

            # Plot the main line
            ax.plot(data.index, data.values,
                    color='#60a5fa',
                    linewidth=3,
                    solid_capstyle='round')

            # Find and plot peaks
            if not data.empty:
                from scipy.signal import find_peaks
                peaks, _ = find_peaks(data.values, distance=60)

                if len(peaks) > 0:
                    peak_values = data.values[peaks]
                    peak_times = data.index[peaks]

                    # Sort peaks by value and get top 2
                    peak_indices = sorted(range(len(peak_values)),
                                          key=lambda k: peak_values[k],
                                          reverse=True)[:2]

                    for idx in peak_indices:
                        ax.annotate(f'{int(peak_values[idx])}',
                                    xy=(peak_times[idx], peak_values[idx]),
                                    xytext=(0, 10),
                                    textcoords='offset points',
                                    ha='center',
                                    va='bottom',
                                    color='white',
                                    fontsize=12,
                                    fontweight='bold')

            # Set y-axis label
            ax.set_ylabel(f'{label}', labelpad=10, fontsize=14,
                          color='white', fontweight='bold')

            # Format x-axis
            ax.xaxis.set_major_formatter(
                matplotlib.dates.DateFormatter('%-I:%M %p'))
            ax.xaxis.set_major_locator(
                matplotlib.dates.HourLocator(interval=3))

            # Style ticks
            if show_x_labels:
                ax.tick_params(axis='both', which='major',
                               labelsize=12, colors='white',
                               labelcolor='white')
                for lbl in ax.get_xticklabels():
                    lbl.set_fontweight('bold')
                    lbl.set_rotation(0)
                    lbl.set_ha('center')  # Center the labels on the tick marks
            else:
                ax.tick_params(axis='x', which='both', length=0)
                ax.set_xticklabels([])

            # Style y-axis ticks
            ax.tick_params(axis='y', which='major',
                           labelsize=16, colors='white',
                           labelcolor='white')
            for lbl in ax.get_yticklabels():
                lbl.set_fontweight('bold')

            # Set y-axis to show only integers
            ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))

            # Remove grid
            ax.grid(False)

            # Set x-axis limits to show full day
            if label == 'Yesterday':
                ax.set_xlim(yesterday_start, today_start)  # Full day from midnight to midnight
            else:
                ax.set_xlim(today_start, tomorrow_start)  # Full day from midnight to midnight

        # Calculate overall maximum for consistent y-axis
        overall_max = max(
            yesterday_data.max() if not yesterday_data.empty else 0,
            today_data.max() if not today_data.empty else 0
        )
        y_max = overall_max * 1.1 if overall_max > 0 else 10

        # Style both subplots
        style_subplot(ax1, yesterday_data, 'Yesterday', show_x_labels=False)
        style_subplot(ax2, today_data, 'Today', show_x_labels=True)

        # Set consistent y-axis limits for both plots
        ax1.set_ylim(bottom=0, top=y_max)
        ax2.set_ylim(bottom=0, top=y_max)

        # Remove spacing between subplots
        plt.subplots_adjust(hspace=0)

        # Save plot
        img = io.BytesIO()
        plt.savefig(img, format='png',
                    facecolor='#1a1a1a',
                    bbox_inches='tight',
                    pad_inches=0.2)
        plt.close()
        img.seek(0)

        return send_file(img, mimetype='image/png')

    except Exception as e:
        print(f"Error generating chart: {e}")
        return "Error generating chart", 500

    finally:
        plt.close('all')
        gc.collect()

if __name__ == '__main__':
    # Set pandas options to minimize memory usage
    pd.options.mode.chained_assignment = None

    # Start the update thread
    update_thread = threading.Thread(target=update_data, daemon=True)
    update_thread.start()

    # Run Flask app
    app.run(host='0.0.0.0', port=5001, threaded=True)
