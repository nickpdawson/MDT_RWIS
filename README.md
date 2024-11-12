# Montana DOT RWIS - Home Assistant Integration

![License](https://img.shields.io/badge/license-MIT-blue.svg)

This Home Assistant custom component integrates the Montana Department of Transportation's (MDT) Road Weather Information System (RWIS) with Home Assistant, allowing users to monitor live weather conditions and access camera feeds at MDT RWIS sites across Montana.

## Features

- **Real-time Weather Data**: Retrieves atmospheric conditions such as temperature, humidity, wind speed, and more.
- **Camera Feeds**: Access live camera images for a selected site.
- **Configurable Update Interval**: Set the frequency of data updates.

## Prerequisites

To use this integration, you must obtain an API key from the Montana Department of Transportation:

1. **Request API Access**:
   - Visit the [MDT ATMS Road Weather Service API Documentation](https://app.mdt.mt.gov/atms/swagger-ui/index.html#/atms-rest-controller/getAllCurrentConditions) page.
   - Submit your contact information to the MDT ATMS Admins via the instructions provided. MDT will contact you with instructions to access the API.

2. **API Update Timing**:
   - RWIS data and camera images are collected every 15 minutes from the start of the hour. To avoid receiving unchanged data, stagger API requests accordingly by setting the update interval in the integration settings.

## Installation

1. **Download the Repository**:
   Clone or download this repository and place it in your `custom_components` directory under `mdt_rwis`:
   ```bash
   custom_components/
   └── mdt_rwis/
       ├── __init__.py
       ├── config_flow.py
       ├── const.py
       ├── sensor.py
       ├── camera.py
       ├── manifest.json
       └── ...
2. **Configure in Home Assistant:**
In the Home Assistant UI, go to Settings > Devices & Services > Add Integration.
Search for Montana DOT RWIS and enter your API key obtained from MDT.


3. **Set Update Interval:**

Configure the update interval in the integration settings to match the 15-minute data refresh schedule.
