<h1 align="center">
  NÖ Smart Meter
</h1>
<h4 align="center">An unofficial python wrapper for the <a href="https://smartmeter.netz-noe.at/#/" target="_blank">EVN - Netz Niederösterreich</a> private API.
</h4>

## Features

- Access energy usage
- Get user & meter information

## Installation

Install with pip:

`pip install noe-smartmeter`

## How To Use

Import the Smartmeter client, provide login information and access available api functions:

```python
from noe_smartmeter import Smartmeter

username = 'YOUR_LOGIN_USER_NAME'
password = 'YOUR_PASSWORD'

offset = 0

api = Smartmeter(username, password)
print(api.get_consumption_since_date("10.09.2023 12:17",offset))
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
