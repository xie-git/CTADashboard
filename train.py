import requests
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta

def get_train_predictions():
    """
    Fetches up to 5 predictions for the Grand (Red Line) CTA station
    using the CTA Train Tracker.
    Returns a list of dictionaries—one for each train.
    """

    # Replace with your valid CTA Train Tracker API key
    API_KEY = "c81446c36907474c9d56442ed2ea9321"

    # CTA Train Tracker endpoint
    API_ENDPOINT = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"

    # mapid for Grand (Red Line) = 40330, request up to 5 arrivals
    params = {
        "key": API_KEY,
        "mapid": "40330",
        "max": "5",
        "outputType": "XML"
    }

    # Mapping from CTA route codes to spelled-out line names
    ROUTE_MAP = {
        "Red":  "Red Line",
        "Blue": "Blue Line",
        "Brn":  "Brown Line",
        "G":    "Green Line",
        "Org":  "Orange Line",
        "Pink": "Pink Line",
        "P":    "Purple Line",
        "Y":    "Yellow Line"
    }

    try:
        # Make API request
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)

        # 1) Grab CTA's reported "current" time from <tmst> (e.g. "20250130 23:59:00")
        tmst_element = root.find(".//tmst")
        cta_now_dt = None
        if tmst_element is not None and tmst_element.text:
            try:
                # Format: "yyyyMMdd HH:mm:ss"
                cta_now_dt = datetime.strptime(tmst_element.text, "%Y%m%d %H:%M:%S")
            except ValueError:
                pass

        # 2) Find all <eta> elements (each is an arrival prediction)
        predictions = root.findall(".//eta")
        if not predictions:
            return []

        train_data = []

        for eta in predictions:
            # --- Route/Line Name ---
            route_code = eta.find('rt').text if eta.find('rt') is not None else "N/A"
            route_name = ROUTE_MAP.get(route_code, f"{route_code} Line")

            # --- Destination (e.g. "Howard", "95th/Dan Ryan") ---
            destNm_element = eta.find('destNm')
            dest_name = destNm_element.text if destNm_element is not None else "Unknown destination"

            # --- Arrival Time (CTA Predicted) ---
            arrT_str = eta.find('arrT').text if eta.find('arrT') is not None else ""

            # Fields to fill
            cta_predicted_arrival_time = "N/A"
            status_str = "N/A"
            actual_time_of_arrival = "N/A"

            try:
                # "arrT" comes as "yyyyMMdd HH:mm:ss"
                arrT_dt = datetime.strptime(arrT_str, "%Y%m%d %H:%M:%S")

                # Convert arrival time to 12-hour format (e.g. "10:40 PM")
                cta_predicted_arrival_time = arrT_dt.strftime("%I:%M %p").lstrip('0')

                # 3) Compare arrT_dt to CTA's current time (cta_now_dt)
                #    fallback to local system time if CTA time is missing
                if cta_now_dt:
                    diff_seconds = (arrT_dt - cta_now_dt).total_seconds()
                    now_dt = cta_now_dt
                else:
                    now_dt = datetime.now()
                    diff_seconds = (arrT_dt - now_dt).total_seconds()

                diff_minutes = int(round(diff_seconds / 60.0))

                # --- Determine status ---
                if diff_minutes < 0:
                    # If arrival time is in the past => "Delayed"
                    status_str = "Delayed"
                elif diff_minutes <= 1:
                    # 0 or 1 => "DUE"
                    status_str = "DUE"
                else:
                    # "X minutes"
                    status_str = f"{diff_minutes} minutes"

                # --- Compute "Actual Time of Arrival" ---
                # If "Delayed", we can't know => "N/A"
                # If "DUE", interpret that as 1 minute from now
                # If "X minutes", parse X
                if status_str == "Delayed":
                    actual_time_of_arrival = "N/A"
                elif status_str == "DUE":
                    # We'll treat DUE as 1 minute away
                    arrival_dt = now_dt + timedelta(minutes=1)
                    actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip('0')
                elif "minutes" in status_str:
                    # Extract the numeric part
                    try:
                        mins_left = int(status_str.split()[0])  # e.g. "5 minutes" => "5"
                        arrival_dt = now_dt + timedelta(minutes=mins_left)
                        actual_time_of_arrival = arrival_dt.strftime("%I:%M %p").lstrip('0')
                    except ValueError:
                        actual_time_of_arrival = "N/A"
                else:
                    # fallback
                    actual_time_of_arrival = "N/A"

            except ValueError:
                # If parsing fails, we leave defaults as "N/A"
                pass

            # Build dictionary for this train
            train_info = {
                "route_name": route_name,              # e.g., "Red Line"
                "destination": dest_name,              # e.g., "Howard"
                "status": status_str,                  # e.g., "DUE", "Delayed", or "5 minutes"
                "cta_predicted_arrival_time": cta_predicted_arrival_time,  # e.g., "10:40 PM"
                "actual_time_of_arrival": actual_time_of_arrival           # e.g., "10:41 PM"
            }
            train_data.append(train_info)

        return train_data

    except Exception as e:
        print(f"Error fetching train data: {str(e)}")
        return []


# Example usage:
if __name__ == "__main__":
    results = get_train_predictions()
    for idx, train_info in enumerate(results, start=1):
        print(
            f"{idx}. Route: {train_info['route_name']}, "
            f"Destination: {train_info['destination']}, "
            f"Status: {train_info['status']}, "
            f"CTA Predicted: {train_info['cta_predicted_arrival_time']}, "
            f"Actual Arrival: {train_info['actual_time_of_arrival']}"
        )