# influx_nut

An interface between Network UPS Tools and influxdb.

This allows sending metrics from NUT to an influxdb database.

## Example configuration

### Config I'm using:

```json
{
	"nut_host": "nutcase",
	"nut_ups": "cp1500avr",
	"nut_vars": {
		"ups.load": {"type": "int", "measurement_name": "ups_load"},
		"input.voltage": {"type": "float", "measurement_name": "ups_voltage"}
	},
	"influx_host": "http://influxbox:8086",
	"influx_creds": ["user", "lamepassword"],
	"influx_db": "systems",
	"influx_tags": {
		"ups": "cp1500avr"
	}
}
```

### Default configuration and documentation thereof (from influx_nut.py):

```python
DEFAULT_CONFIG = {
    # interval between updates, in seconds
    'interval': 20,
    # ip/hostname of NUT server
    'nut_host': '127.0.0.1',
    # NUT port
    'nut_port': 3493,
    # UPS name on that NUT server
    'nut_ups': 'ups1',

    # variables from NUT to send to influxdb, see above
    # example in json:
    # "nut_vars": {
    #   "ups.realpower.nominal": {
    #        "type": "int",
    #        "measurement_name": "ups1_power"
    #   }
    # }
    'nut_vars': {},

    # proto://host:port of influxdb. Please don't add a trailing slash.
    'influx_host': 'http://127.0.0.1:8086', 

    # database on the influx server
    'influx_db': 'systems',

    # tags to add to influxdb measurements
    'influx_tags': {},

    # credentials for influxdb
    # example in json:
    # "influx_creds": ["user", "sekrit"]
    'influx_creds': None
}
```