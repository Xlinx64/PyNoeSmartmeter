<h1 align="center">
  NÖ Smart Meter
</h1>
<h4 align="center">An unofficial python wrapper for the <a href="https://smartmeter.netz-noe.at/#/" target="_blank">EVN - Netz Niederösterreich</a> private API.
</h4>

<h2>
  WARNING: This library is still work in progress and might change a lot!
  This project will be used in a home assistant integration. 
</h2>


## Features

- Access energy usage
- Get user & meter information

This library is currently written for asynchronous use. There might be a synchronous version in the future.

## Installation

Install with pip:

`pip install pynoesmartmeter`

## How To Use

Import the Smartmeter client, provide login information and access available api functions:

```python
import asyncio
from pynoesmartmeter import Smartmeter

username = 'YOUR_LOGIN_USER_NAME'
password = 'YOUR_PASSWORD'

OFFSET = 0

api = Smartmeter(USERNAME, PASSWORD)
asyncio.run(api.get_consumption_since_date("24.03.2024 10:03", OFFSET))

```


## Awesome projects
- **EVN_Smartmeter_Wrapper** from A.E.I.O.U. (https://www.lteforum.at/mobilfunk/evn-smartmeter-api-wrapper-influx-importer-grafana-dashboard.21319/) \
I used his code as the base for this project.
- **vienna-smartmeter** from platysma (https://github.com/platysma/vienna-smartmeter) \
I used this project as a starting point. (I even stole the readme)

## License

> You can check out the full license [here](https://github.com/xilinx64/vienna-smartmeter/blob/main/LICENSE)

This project is licensed under the terms of the **MIT** license.

## Legal

Disclaimer: This is not affliated, endorsed or certified by Netz Niederösterreich GmbH. This is an independent and unofficial API. Strictly not for spam. Use at your own risk.
