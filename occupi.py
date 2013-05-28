import collections
import json
import logging
import logging.handlers
import requests
import sensors, sensors.dummy
import subprocess
import time

from requests.exceptions import ConnectionError

API_KEY               =  'API KEY HERE'
API_UPDATE_INTERVAL   =  300 # Check in every 5m
API_URL               =  'URL TO POST TO HERE'
COUNT_INTERVAL        =  360
DATA_BUFFER_SIZE      =  2 # Number of API_UPDATE_INTERVALs held in memory
GRAPH_SIZE            =  5
HAS_GPIO              =  True
INCREMENT_EMPTY       =  1
INCREMENT_OCCUPIED    =  32
LOG_FILE_PATH         =  '/var/log/occupi.log'
LOG_LEVEL             =  logging.INFO
PID_FILE_PATH         =  '/var/run/occupi.pid'
PIN_INPUT_PIR         =  18
PIN_OUTPUT_LED        =  25
ROOM_ID               =  'ROOM-0'
SENSE_PCT             =  0.6
SENSOR_POLL_INTERVAL  =  0.5
STATE_EMPTY           =  0
STATE_OCCUPIED        =  1

STATE_DEFAULT         =  STATE_EMPTY

from config import *

if HAS_GPIO == True:
	import RPi.GPIO as io
	import sensors.rpi

class Occupi:

	def __init__ ( self ):
		self.state_different_count  =  0
		self.state                  =  None
		self.state_ts               =  None
		self.updated_ts             =  time.time( )

		# Ring buffer to store up to DATA_BUFFER_SIZE update intervals
		# worth of data
		n_per_update_interval  =  ( API_UPDATE_INTERVAL / SENSOR_POLL_INTERVAL )
		max_data_in_memory     =  n_per_update_interval * DATA_BUFFER_SIZE
		self.data_buffer       =  collections.deque( maxlen=max_data_in_memory )


	def run ( self ):
		# Set up Logging
		logger  =  logging.getLogger( self.__class__.__name__ )
		logger.setLevel( LOG_LEVEL )

		formatter  =  logging.Formatter(
			fmt='%(asctime)s - %(room_id)s - %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
			)

		handler  =  logging.handlers.RotatingFileHandler( LOG_FILE_PATH, maxBytes=1024*1024*20, backupCount=5 )
		handler.setFormatter( formatter )
		logger.addHandler( handler )

		self.logger  =  logging.LoggerAdapter( logger, {
			'room_id' : ROOM_ID
			} )

		self.logger.info( "Starting" )

		# Set up GPIO
		if HAS_GPIO == True:
			io.setwarnings( False )
			io.setmode( io.BCM )
			io.setup( PIN_OUTPUT_LED, io.OUT )
			self.sensor  =  sensors.rpi.PIRSensor( PIN_INPUT_PIR )
		else:
			self.sensor  =  sensors.dummy.DummySensor( )

		self.logger.info( "GPIO pins wired" )

		self.change_state( STATE_DEFAULT )

		self.logger.info( "Initial state set" )

		self.logger.info( "Startup complete." )

		try:
			while True:
				now_ts        =  time.time( )
				sensed_state  =  self.sense_state( )

				self.handle_sensed_state( self.state, sensed_state, now_ts )

				if now_ts - self.updated_ts > API_UPDATE_INTERVAL:
					self.post_state_to_api( self.state )

				time.sleep( SENSOR_POLL_INTERVAL )
		except Exception, err:
			self.logger.exception( 'Error in main loop:' )


	def format_state ( self, state ):
		if state == STATE_EMPTY:
			return "EMPTY"
		elif state == STATE_OCCUPIED:
			return "OCCUPIED"
		else:
			return "UNKNOWN"


	def format_time ( self, ts ):
		return time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( ts ) )


	def change_state ( self, new_state ):

		if new_state == self.state:
			return

		now_ts  =  time.time( )

		if self.state_ts != None:
			state_length_sec  =  round( now_ts - self.state_ts )
			msg  =  "%s - was %s for %d seconds" % (
				self.format_state( new_state ),
				self.format_state( self.state ),
				state_length_sec
				)
		else:
			msg  =  "%s" % self.format_state( new_state )

		self.logger.info( msg )

		if new_state == STATE_EMPTY:
			self.light_led( False )
		elif new_state == STATE_OCCUPIED:
			self.light_led( True )

		self.state     =  new_state
		self.state_ts  =  now_ts

		self.post_state_to_api( self.state )


	def post_state_to_api ( self, state ):

		self.updated_ts  =  time.time( )

		p  =  { 'occupied' : state, 'key' : API_KEY,
			'data' : list( self.data_buffer )
			}

		try:
			r  =  requests.post( API_URL, data=p )
		except ConnectionError as e:
			self.logger.info( "Error contacting API: %s" % e )
			self.logger.info( "Would have sent to API: %s" % json.dumps( p ) )
		else:
			self.logger.info( "Sent %-10s to API, status: %d" % ( self.format_state( state ), r.status_code ) )
			self.data_buffer.clear( )


	def get_count_to_change ( self, state ):
		return int( COUNT_INTERVAL / SENSOR_POLL_INTERVAL * SENSE_PCT )


	def light_led ( self, on_or_off ):
		if HAS_GPIO == False:
			return
		elif on_or_off == True:
			io.output( PIN_OUTPUT_LED, io.HIGH )
		else:
			io.output( PIN_OUTPUT_LED, io.LOW )


	def handle_sensed_state ( self, state, sensed_state, now_ts ):

		# Record the raw state
		self.data_buffer.append( ( now_ts, sensed_state ) )

		count_to_change  =  self.get_count_to_change( state )

		if sensed_state == STATE_OCCUPIED:
			increment  =  INCREMENT_OCCUPIED
		else:
			increment  =  INCREMENT_EMPTY

		if sensed_state != state:
			self.state_different_count  +=  increment 
		elif self.state_different_count > 0:
			self.state_different_count  -=  increment

		if state == STATE_OCCUPIED:
			graph_amount  =  count_to_change - self.state_different_count
		else:
			graph_amount  =  self.state_different_count

		msg  =  "%-10s: sensed %-10s [%-5s] %3d" % (
			self.format_state( state ),
			self.format_state( sensed_state ),
			self.string_graph( graph_amount, count_to_change, GRAPH_SIZE ),
			graph_amount
			)
		self.logger.debug( msg )

		if self.should_change_state( state, self.state_different_count ):
			self.change_state( sensed_state )
			self.state_different_count  =  0


	def sense_state ( self ):
		if self.sensor.read( ):
			return STATE_OCCUPIED
		else:
			return STATE_EMPTY


	def should_change_state ( self, state, different_count ):
		count_to_change  =  self.get_count_to_change( state )

		if different_count >= count_to_change:
			return True
		else:
			return False


	def string_graph ( self, n, max, size ):
		n_ticks  =  int( float( n ) / float( max ) * float( size ) )
		output  =  ""
		for i in range( 0, n_ticks ):
			output  =  output + "#"
		return output


if __name__ == '__main__':
	occupi  =  Occupi( )
	occupi.run( )
