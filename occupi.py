import requests
import subprocess
import time
import RPi.GPIO as io

API_KEY               =  'API KEY HERE'
API_UPDATE_INTERVAL   =  300 # Check in every 5m
API_URL               =  'URL TO POST TO HERE'
COUNT_INTERVAL        =  120
GRAPH_SIZE            =  5
PIN_INPUT_PIR         =  18
PIN_OUTPUT_LED        =  25
SENSE_PCT             =  0.6
SENSOR_POLL_INTERVAL  =  0.5
STATE_EMPTY           =  0
STATE_OCCUPIED        =  1

STATE_DEFAULT         =  STATE_EMPTY

from config import *

start_ts     =  time.time( )
empty_ts     =  start_ts
occupied_ts  =  start_ts

updated_ts   =  None

state_different_count  =  0

state = None

# Set up GPIO
io.setwarnings( False )
io.setmode( io.BCM )
io.setup( PIN_INPUT_PIR, io.IN )
io.setup( PIN_OUTPUT_LED, io.OUT )

def format_state ( state ):
	if state == STATE_EMPTY:
		return "EMPTY"
	elif state == STATE_OCCUPIED:
		return "OCCUPIED"
	else:
		return "UNKNOWN"


def format_time ( ts ):
	return time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( ts ) )


def output ( message ):
	print "%s: %s" % ( format_time( time.time( ) ), message )


def change_state ( new_state ):
	global state, empty_ts, occupied_ts

	if new_state == state:
		return

	now_ts  =  time.time( )
	output( format_state( new_state ) )

	if new_state == STATE_EMPTY:
		empty_ts  =  now_ts
		light_led( False )
	elif new_state == STATE_OCCUPIED:
		occupied_ts  =  now_ts
		light_led( True )
	state  =  new_state
	post_state_to_api( state )

def post_state_to_api ( state ):
	global updated_ts

	p  =  { 'occupied' : state, 'key' : API_KEY, 'ip' : determine_ip( ) }
	r  =  requests.post( API_URL, data=p )
	output( "Sent to API, status: %d" % r.status_code )
	updated_ts  =  time.time( )


def determine_ip ( ):
	ip_string  =  subprocess.check_output( ["hostname", "-I"] )
	return ip_string


def get_count_to_change ( state ):
	return int( COUNT_INTERVAL / SENSOR_POLL_INTERVAL * SENSE_PCT )


def light_led ( on_or_off ):
	if on_or_off == True:
		io.output( PIN_OUTPUT_LED, io.HIGH )
	else:
		io.output( PIN_OUTPUT_LED, io.LOW )


def handle_sensed_state ( state, sensed_state ):
	global state_different_count

	count_to_change  =  get_count_to_change( state )

	if sensed_state == STATE_OCCUPIED:
		increment  =  4
	else:
		increment  =  1

	if sensed_state != state:
		state_different_count  +=  increment 
	elif state_different_count > 0:
		state_different_count  -=  increment

	if state == STATE_OCCUPIED:
		graph_amount  =  count_to_change - state_different_count
	else:
		graph_amount  =  state_different_count

	output( "%-10s: sensed %-10s [%-5s] %3d" % ( format_state( state ), format_state( sensed_state ), string_graph( graph_amount, count_to_change, GRAPH_SIZE ), graph_amount ) )

	if should_change_state( state, state_different_count ):
		change_state( sensed_state )
		state_different_count  =  0


def sense_state ( ):
	if io.input( PIN_INPUT_PIR ):
		return STATE_OCCUPIED
	else:
		return STATE_EMPTY


def should_change_state ( state, different_count ):
	count_to_change  =  get_count_to_change( state )

	if different_count >= count_to_change:
		return True
	else:
		return False


def string_graph ( n, max, size ):
	n_ticks  =  int( float( n ) / float( max ) * float( size ) )
	output  =  ""
	for i in range( 0, n_ticks ):
		output  =  output + "#"
	return output


if __name__ == '__main__':
	output( "Starting" )
	change_state( STATE_DEFAULT )

	try:
		while True:
			now_ts        =  time.time( )
			sensed_state  =  sense_state( )

			handle_sensed_state( state, sensed_state )

			if now_ts - updated_ts > API_UPDATE_INTERVAL:
				post_state_to_api( state )

			time.sleep( SENSOR_POLL_INTERVAL )

	except KeyboardInterrupt:
		change_state( STATE_DEFAULT )
		output( "Exiting after keyboard interrupt" )
		exit( )
