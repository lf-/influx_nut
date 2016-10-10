import setuptools

setuptools.setup(
	name = 'influx_nut',
	version = '0.0.1',
	py_modules = ['influx_nut'],
	install_requires = ['requests'],
	entry_points = {
		'console_scripts': [
			'influx_nut=influx_nut:cli'
		]
	},

	author = 'lf',
	author_email = 'github@lfcode.ca',
	description = 'Simple interface between NUT and influxdb',
	license = 'MIT',
	keywords = 'influxdb nut',
	url = 'https://github.com/lf-/influx_nut'
)