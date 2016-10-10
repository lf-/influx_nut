import socket
import collections
import time
import json
import os
import sys
from typing import Tuple, Mapping, Iterable

import requests


__doc__ = """A small daemon and library for sending NUT statistics to influxdb"""

DEFAULT_CONFIG = {
    'interval': 20,
    'nut_host': '127.0.0.1',
    'nut_port': 3493,
    'nut_ups': 'ups1',
    # example in json:
    # "nut_vars": {
    #   "ups.realpower.nominal": {
    #        "type": "int",
    #        "measurement_name": "ups1_power"
    #   }
    # }
    'nut_vars': {},
    'influx_host': 'http://127.0.0.1:8086',
    'influx_db': 'systems',
    'influx_tags': {},
    # example in json:
    # "influx_creds": ["user", "sekrit"]
    'influx_creds': None
}

# types allowed in nut_vars in the config
CONFIG_TYPES = {
    'float': float,
    'int': int,
    'str': str,
    'bool': bool
}


class RequestError(Exception):
    pass


class InfluxDataPoint:
    def __init__(self, measurement, fields, tags: dict = {},
                 timestamp=None, timestamp_precision='n'):
        """
        Object representing a data point to be sent to influxdb

        Parameters:
        measurement -- measurement name
        fields -- dict of field key-value pairs
        tags -- optional: dict of tags to add to the measurement
        timestamp -- optional: UTC timestamp for measurement
        timestamp_precision -- optional: precision of timestamp value.
                               Format: SI prefix as single character
                               (n, u, m, s, h)
                               Assumed to be nanoseconds if not
                               specified
        """
        self.measurement = measurement
        self.tags = tags
        self.fields = fields
        self.timestamp = timestamp
        self.timestamp_precision = timestamp_precision

    @staticmethod
    def _format_field_value(val):
        if isinstance(val, str):
            return '"{}"'.format(val)
        else:
            return str(val)

    @classmethod
    def _fieldkeyvaluepairs(cls, d: Mapping):
        return ['{}={}'.format(k, cls._format_field_value(v)) \
                for k, v in d.items()]

    @classmethod
    def _keyvaluepairs(cls, d: Mapping):
        return ['{}={}'.format(k, v) for k, v in d.items()]

    def __repr__(self):
        return ('{p.__class__.__name__}({p.measurement!r}, {p.fields!r}, '
               'tags={p.tags!r}, timestamp={p.timestamp!r}, '
               'timestamp_precision={p.timestamp_precision!r})'
               .format(p=self))

    def __str__(self):
        if self.tags:
            tag_str = ',' + ','.join(type(self)._keyvaluepairs(self.tags))
        else:
            tag_str = ''
        if self.timestamp is not None:
            timestamp = ' {}'.format(self.timestamp)
        else:
            timestamp = ''

        fields_str = ','.join(type(self)._fieldkeyvaluepairs(self.fields))
        return ('{p.measurement}{tags} {fields}{timestamp}'
               .format(p=self, tags=tag_str, fields=fields_str,
                       timestamp=timestamp).rstrip())


class NUTConnection:
    def __init__(self, addr, port=3493):
        """
        Parameters:
        addr -- address to connect to
        port -- port number on that address
        """
        self.addr = addr
        self.port = port
        self.connection = None
        self.connect()

    def request_var(self, ups, var) -> str:
        """
        Requests the value of a NUT variable

        Parameters:
        ups -- ups to get the variable from
        var -- variable name

        Returns:
        Value of the variable as a string
        """
        VarResponse = collections.namedtuple('VarResponse',
                                             ('type', 'ups', 'var', 'value'))
        req = 'GET VAR {} {}'.format(ups, var)
        raw_resp = self.request(req)
        resp = VarResponse(*(raw_resp.split(' ')))
        return resp.value.strip('"')

    def request_list(self, thing):
        """
        Requests a list of something from the NUT daemon

        Parameters:
        thing -- thing to request a list of, for example,
                 'UPS', or 'VAR <upsname>'

        Returns:
        List of entries in the returned list

        Example:
        >>> nc = NUTConnection('upsdbox')
        >>> nc.request_list('UPS')
        ['UPS cp1500avr "Description unavailable"']
        """
        if self.connection is None:
            raise RuntimeError('Not connected to NUT')

        self.connection.send('LIST {}\n'.format(thing).encode())
        resp = []
        # pull and concat all the parts of the response;
        # NUT seems to send(header); compute_reponse();
        #              send(response); send(footer)
        while True:
            resp_part = self._receive()
            resp.extend(resp_part)
            if resp_part.endswith('END LIST {}\n'.format(thing)):
                break

        resp_lines = ''.join(resp).split('\n')
        # nuke header and footer
        return resp_lines[1:-2]

    def request(self, req):
        """
        Send a request to the NUT daemon

        Parameters:
        req -- request to make. *Will be newline terminated for you*
        """
        if self.connection is None:
            raise RuntimeError('Not connected to NUT')
        self.connection.send((req + '\n').encode())
        resp = self._receive().rstrip('\n')
        if resp.startswith('ERR'):
            raise RequestError(resp)
        else:
            return resp

    def disconnect(self):
        """
        Disconnect from NUT upsd
        """
        self.connection.close()

    def connect(self):
        self.connection = socket.socket()
        # arbitrary timeout of 2s, nothing should take longer than that
        self.connection.settimeout(2)
        self.connection.connect((self.addr, self.port))

    def _receive(self):
        return self.connection.recv(4096).decode('utf-8')

    def __repr__(self):
        return '{c.__class__.__name__}({c.addr}, port={c.port})'.format(c=self)


def send_influx(host, database, datapoints: Iterable[InfluxDataPoint], creds=None):
    """
    Sends some data to an influxdb database

    Parameters:
    host -- proto://host:port that influxdb is on
    database -- database to put data in
    datapoints -- InfluxDataPoint objects to send
    creds -- (username, password) tuple to authenticate
    """
    query_str = {'db': database}
    if creds is not None:
        query_str.update({'u': creds[0], 'p': creds[1]})

    for datapoint in datapoints:
        if (datapoint.timestamp_precision is not None and
                datapoint.timestamp is not None):
            query_str.update({'precision': datapoint.timestamp_precision})

    data = b'\n'.join([str(datapoint).encode() for datapoint in datapoints])
    print(host, query_str, data)
    requests.post(host + '/write', params=query_str, data=data)


def update(influx_host, influx_db, nut_conn: NUTConnection,
           nut_vars: Mapping[str, type], nut_ups, influx_tags={},
           influx_creds: Tuple[str, str] = None):
    """
    Update the influx database with some NUT vars

    Parameters:
    influx_host -- proto://host:port running influxdb
    influx_db -- database name for influx
    nut_vars -- dict of name: type_to_convert_to for variables from NUT
    nut_conn -- NUTConnection object connected to a server
    nut_ups -- NUT UPS to update influx with

    influx_tags -- tags to send with the update
    influx_creds -- (username, password) tuple
    """
    datapoints = []
    for var, info in nut_vars.items():
        try:
            var_value = info['type'](nut_conn.request_var(nut_ups, var))
        except RequestError as e:
            print('RequestError: {}, skipping!'.format(e.args), file=sys.stderr)
            continue
        datapoints.append(InfluxDataPoint(info['measurement_name'],
                                      {'value': var_value}, tags=influx_tags))
    send_influx(influx_host, influx_db, datapoints, creds=influx_creds)


def _recursive_update(d: Mapping, u: Mapping):
    """
    Recursively update a dictionary

    Parameters:
    d -- dictionary to update
    u -- updated mapping
    """
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = _recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def _load_config(file):
    """
    Load JSON based config from a file

    Parameters:
    file -- filename string or fp
    """
    new_config = DEFAULT_CONFIG.copy()
    if file is None:
        user_config = {}
    else:
        with open(file) as f:
            user_config = json.load(f)
    _recursive_update(new_config, user_config)
    # convert the strings in nut_vars to real types to simplify conversion
    for _, var in new_config['nut_vars'].items():
        var['type'] = CONFIG_TYPES[var['type']]
    return new_config


def cli():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', help='config file')
    args = p.parse_args()
    config = _load_config(args.config)

    nc = NUTConnection(config['nut_host'], port=config['nut_port'])
    while True:
        update(config['influx_host'], config['influx_db'], nc,
               config['nut_vars'], config['nut_ups'],
               influx_tags=config['influx_tags'],
               influx_creds=config['influx_creds'])
        time.sleep(config['interval'])


if __name__ == '__main__':
    cli()
