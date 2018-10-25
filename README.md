# influx_nut

An interface between Network UPS Tools and influxdb.

This allows sending metrics from NUT to an influxdb database.

## Getting started

```
# cd /path/to/git/clone
# pip3 install .
# cp config.example.json /etc/influx_nut.json  # edit to set up for your needs
$ influx_nut --config /etc/influx_nut.json
```

## Example configuration

### UPS load and voltage reporting

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

### Config documentation

#### `interval`

How frequently is the data sent to Influx in seconds? Default: `20`.

#### `nut_host`

Hostname NUT is accessible at. Default: `"127.0.0.1"`.

#### `nut_port`

Port number to use to connect to the NUT server. Default: `3493`.

#### `nut_ups`

UPS name on that NUT server. Default: `"ups1"`.

#### `nut_vars`

Variables to send from NUT to influxdb. Example:

```json
"nut_vars": {
  "ups.realpower.nominal": {
     "type": "int",
     "measurement_name": "ups1_power"
  }
}
```

Valid types are "float", "int", "bool", and "str".

#### `influx_host`

URL of influxdb server to send data to, without a trailing slash.
Default: `"http://127.0.0.1:8086"`.

#### `influx_db`

Database on the influxdb server to put data in. Default: `"systems"`.

#### `influx_tags`

Tags (in mapping form) to send to the influxdb server. These are static for
all measurements sent from influx_nut.
Example:

```json
{"tag1": "value1", "tag2": "value2"}
```

#### `influx_creds`

Credentials to use to connect to the influxdb server. Example: `["user", "sekrit"]`.
Default is `null` (no authentication).
