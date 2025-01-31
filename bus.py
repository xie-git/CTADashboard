import requests
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta

def get_bus_predictions():
    """
    Fetches bus predictions for a given stop.
    Returns a list of dictionaries—one for each bus arrival.
    Each dictionary includes:
      - route
      - status (Delayed, DUE, or X minutes)
      - cta_predicted_arrival_time (parsed from 'prdtm')
      - actual_time_of_arrival (CTA current time + X minutes)
      - distance (in feet or miles)
    """

    API_ENDPOINT = "http://www.ctabustracker.com/bustime/api/v2/getpredictions"
    API_KEY = "iyNEKq4gFyHRMZkHN9jFVVADG"
    STOP_ID = "2192"  # e.g., Michigan & Randolph

    params = {
        "key": API_KEY,
        "stpid": STOP_ID,
        "format": "xml"
    }

    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        # Find the <tmstmp> element (the bus API's current time)
        tmst_element = root.find(".//tmstmp")
        cta_now_dt = None
        if tmst_element is not None and tmst_element.text:
            time_str = tmst_element.text  # e.g., "20250130 21:29"
            try:
                # This format has no seconds
                cta_now_dt = datetime.strptime(time_str, "%Y%m%d %H:%M")
            except ValueError:
                # If there's a fallback scenario with seconds, you could try:
                # try:
                #     cta_now_dt = datetime.strptime(time_str, "%Y%m%d %H:%M:%S")
                # except ValueError:
                #     pass
                pass

        # 2) Find all <prd> elements (each is a prediction)
        predictions = root.findall(".//prd")

        if not predictions:
            return []

        bus_data = []

        for prd in predictions:
            # --- Route Number ---
            route_element = prd.find("rt")
            route = route_element.text if route_element is not None else "N/A"

            # --- Predicted Countdown in minutes (or "DUE") ---
            prdctdn_element = prd.find("prdctdn")
            raw_countdown_str = prdctdn_element.text if prdctdn_element is not None else "N/A"

            # --- CTA Predicted Arrival Time (prdtm) ---
            prdtm_element = prd.find("prdtm")
            cta_predicted_arrival_time = "N/A"

            # --- Distance Calculation (Feet or Miles) ---
            dstp_element = prd.find("dstp")
            distance_str = "N/A"
            if dstp_element is not None and dstp_element.text:
                try:
                    distance_ft = float(dstp_element.text)
                    if distance_ft <= 1000:
                        distance_str = f"{distance_ft:.0f} ft"
                    else:
                        distance_mi = distance_ft / 5280.0
                        distance_str = f"{distance_mi:.2f} mi"
                except ValueError:
                    pass

            # Defaults
            status_str = "N/A"
            actual_time_of_arrival = "N/A"

            # Parse the CTA predicted arrival time (prdtm)
            if prdtm_element is not None and prdtm_element.text:
                # Format might be "YYYYMMDD HH:MM" (Bus Tracker style)
                try:
                    prdtm_dt = datetime.strptime(prdtm_element.text, "%Y%m%d %H:%M")
                    # Convert to 12-hour format
                    cta_predicted_arrival_time = prdtm_dt.strftime("%I:%M %p").lstrip("0")
                except ValueError:
                    pass

            # Next, figure out the minutes until arrival from our perspective
            # We'll prefer to rely on cta_now_dt if available
            # If it's "DUE" or numeric, we handle it
            if cta_now_dt:
                # We'll compute minutes from the difference prdtm_dt - cta_now_dt
                if prdtm_element is not None and prdtm_element.text:
                    try:
                        prdtm_dt = datetime.strptime(prdtm_element.text, "%Y%m%d %H:%M")
                        diff_seconds = (prdtm_dt - cta_now_dt).total_seconds()
                        diff_minutes = int(round(diff_seconds / 60.0))

                        if diff_minutes < 0:
                            status_str = "Delayed"
                        elif diff_minutes <= 1:
                            status_str = "DUE"
                        else:
                            status_str = f"{diff_minutes} minutes"

                        # Compute Actual Arrival Time
                        if status_str == "Delayed":
                            actual_time_of_arrival = "N/A"
                        elif status_str == "DUE":
                            # We'll treat DUE as 1 minute from now
                            arrival_dt = cta_now_dt + timedelta(minutes=1)
                            actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip("0")
                        elif "minutes" in status_str:
                            # e.g. "5 minutes"
                            try:
                                mins_left = int(status_str.split()[0])
                                arrival_dt = cta_now_dt + timedelta(minutes=mins_left)
                                actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip("0")
                            except ValueError:
                                pass

                    except ValueError:
                        pass

                else:
                    # If no prdtm or parsing failed, fallback to the raw prdctdn if numeric
                    try:
                        mins_left = int(raw_countdown_str)
                        if mins_left < 0:
                            status_str = "Delayed"
                            actual_time_of_arrival = "N/A"
                        elif mins_left <= 1:
                            status_str = "DUE"
                            arrival_dt = cta_now_dt + timedelta(minutes=1)
                            actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip("0")
                        else:
                            status_str = f"{mins_left} minutes"
                            arrival_dt = cta_now_dt + timedelta(minutes=mins_left)
                            actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip("0")
                    except ValueError:
                        # Could be "DUE" or something else
                        if raw_countdown_str.upper() == "DUE":
                            status_str = "DUE"
                            arrival_dt = cta_now_dt + timedelta(minutes=1)
                            actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip("0")

            else:
                # If we don't have CTA's current time, we fallback to prdctdn logic
                # This is less accurate, but still workable
                if raw_countdown_str.isdigit():
                    mins_left = int(raw_countdown_str)
                    if mins_left < 0:
                        status_str = "Delayed"
                        actual_time_of_arrival = "N/A"
                    elif mins_left <= 1:
                        status_str = "DUE"
                        # We can't compute an actual arrival time without a reference,
                        # so let's just do "N/A" or a local time
                        actual_time_of_arrival = "N/A"
                    else:
                        status_str = f"{mins_left} minutes"
                        actual_time_of_arrival = "N/A"
                else:
                    # Possibly "DUE" or something else
                    if raw_countdown_str.upper() == "DUE":
                        status_str = "DUE"
                    # actual_time_of_arrival remains "N/A"

            # Build the final dictionary
            bus_info = {
                "route": route,
                "status": status_str,  # e.g. "DUE", "Delayed", or "5 minutes"
                "cta_predicted_arrival_time": cta_predicted_arrival_time,  # e.g. "10:40 PM"
                "actual_time_of_arrival": actual_time_of_arrival,          # e.g. "10:41 PM"
                "distance": distance_str
            }
            bus_data.append(bus_info)

        return bus_data

    except Exception as e:
        print(f"Error fetching bus data: {str(e)}")
        return []


# Example usage:
if __name__ == "__main__":
    results = get_bus_predictions()
    for idx, bus_info in enumerate(results, start=1):
        print(
            f"{idx}. Route: {bus_info['route']}, "
            f"Status: {bus_info['status']}, "
            f"CTA Predicted: {bus_info['cta_predicted_arrival_time']}, "
            f"Actual Arrival: {bus_info['actual_time_of_arrival']}, "
            f"Distance: {bus_info['distance']}"
        )