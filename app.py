from flask import Flask, render_template
from datetime import datetime
from zoneinfo import ZoneInfo

import bus
import train

app = Flask(__name__)

@app.route("/")
def home():
    # Hard-coded names for demonstration
    BUS_STOP_NAME = "Placeholder Bus Stop Name"   # For the bus stop ID 156
    TRAIN_STATION_NAME = "Grand (Red Line)"        # For the train station ID 40330

    # Fetch bus and train data
    bus_results = bus.get_bus_predictions()        # list of dict
    train_results = train.get_train_predictions()  # list of dict

    # Convert current time to America/Chicago
    chicago_tz = ZoneInfo("America/Chicago")
    chicago_now = datetime.now(tz=chicago_tz)  # or datetime.now(chicago_tz)
    # Format as HH:MM AM/PM, removing leading zero if any
    current_time = chicago_now.strftime("%I:%M %p").lstrip("0")

    return render_template(
        "index.html",
        bus_info=bus_results,
        train_info=train_results,
        bus_stop_name=BUS_STOP_NAME,
        train_station_name=TRAIN_STATION_NAME,
        current_time=current_time
    )

if __name__ == "__main__":
    # For local testing
    app.run(debug=True, host="0.0.0.0", port=5001)