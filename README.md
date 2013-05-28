# occupi

`occupi` is a simple occupancy detector designed to run on the Raspberry Pi,
using the passive infrared (PIR)
[sensor module](http://www.adafruit.com/products/189) from Adafruit.

## Requirements
You will need the following Python modules:
 - python-daemon
 - requests
 - RPi.GPIO (if you set HAS_GPIO = True)

All are installable with pip.

## Setup
Copy the `config.template.py` file and update API_KEY and API_URL.

## Running from the command line
`python occupi.py`

## Running as a daemon
`python occupid.py start`

## Run on startup
See the `init-script` directory for a sample file you can place in
`/etc/init.d`
