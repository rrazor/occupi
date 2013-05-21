import logging
import logging.handlers
import requests
import subprocess
import time
import RPi.GPIO as io

from daemon import runner

API_KEY               =  'API KEY HERE'
API_UPDATE_INTERVAL   =  300 # Check in every 5m
API_URL               =  'URL TO POST TO HERE'
COUNT_INTERVAL        =  120
GRAPH_SIZE            =  5
INCREMENT_EMPTY       =  1
INCREMENT_OCCUPIED    =  4
LOG_FILE_PATH         =  '/var/log/occupi.log'
PID_FILE_PATH         =  '/var/run/occupi.pid'
PIN_INPUT_PIR         =  18
PIN_OUTPUT_LED        =  25
SENSE_PCT             =  0.6
SENSOR_POLL_INTERVAL  =  0.5
STATE_EMPTY           =  0
STATE_OCCUPIED        =  1

STATE_DEFAULT         =  STATE_EMPTY

from config import *

class Occupi:

	def __init__ ( self ):
		self.state_different_count  =  0
		self.state                  =  None
		self.updated_ts             =  None

		# Daemon-related atttributes
		self.stdin_path       =  '/dev/null'
		self.stdout_path      =  '/dev/tty'
		self.stderr_path      =  '/dev/tty'
		self.pidfile_path     =  PID_FILE_PATH
		self.pidfile_timeout  =  5


	def run ( self ):
		# Set up Logging
		self.logger  =  logging.getLogger( self.__class__.__name__ )
		self.logger.setLevel( logging.INFO )

		formatter  =  logging.Formatter(
			fmt='%(asctime)s - %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
			)

		handler  =  logging.handlers.RotatingFileHandler( LOG_FILE_PATH, maxBytes=1024*1024*20, backupCount=5 )
		handler.setFormatter( formatter )

		self.logger.addHandler( handler )

		self.info( "Starting" )

		# Set up GPIO
		io.setwarnings( False )
		io.setmode( io.BCM )
		io.setup( PIN_INPUT_PIR, io.IN )
		io.setup( PIN_OUTPUT_LED, io.OUT )

		self.info( "GPIO pins wired" )

		self.change_state( STATE_DEFAULT )

		self.info( "Initial state set" )

		self.info( "Startup complete." )

		while True:
			now_ts        =  time.time( )
			sensed_state  =  self.sense_state( )

			self.handle_sensed_state( self.state, sensed_state )

			if now_ts - self.updated_ts > API_UPDATE_INTERVAL:
				self.post_state_to_api( self.state )

			time.sleep( SENSOR_POLL_INTERVAL )

	def format_state ( self, state ):
		if state == STATE_EMPTY:
			return "EMPTY"
		elif state == STATE_OCCUPIED:
			return "OCCUPIED"
		else:
			return "UNKNOWN"


	def format_time ( self, ts ):
		return time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( ts ) )


	def info ( self, message ):
		self.logger.info( message )

	def debug ( self, message ):
		self.logger.debug( message )


	def change_state ( self, new_state ):

		if new_state == self.state:
			return

		now_ts  =  time.time( )
		self.info( self.format_state( new_state ) )

		if new_state == STATE_EMPTY:
			self.light_led( False )
		elif new_state == STATE_OCCUPIED:
			self.light_led( True )
		self.state  =  new_state
		self.post_state_to_api( self.state )

	def post_state_to_api ( self, state ):

		p  =  { 'occupied' : state, 'key' : API_KEY, 'ip' : self.determine_ip( ) }
		r  =  requests.post( API_URL, data=p )
		self.info( "Sent %-10s to API, status: %d" % ( self.format_state( state ), r.status_code ) )
		self.updated_ts  =  time.time( )


	def determine_ip ( self ):
		ip_string  =  subprocess.check_output( ["hostname", "-I"] )
		return ip_string


	def get_count_to_change ( self, state ):
		return int( COUNT_INTERVAL / SENSOR_POLL_INTERVAL * SENSE_PCT )


	def light_led ( self, on_or_off ):
		if on_or_off == True:
			io.output( PIN_OUTPUT_LED, io.HIGH )
		else:
			io.output( PIN_OUTPUT_LED, io.LOW )


	def handle_sensed_state ( self, state, sensed_state ):

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
		self.debug( msg )

		if self.should_change_state( state, self.state_different_count ):
			self.change_state( sensed_state )
			self.state_different_count  =  0


	def sense_state ( self ):
		if io.input( PIN_INPUT_PIR ):
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
	daemon_runner  =  runner.DaemonRunner( occupi )
	daemon_runner.do_action( )
