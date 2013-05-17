#!/usr/bin/python2.7

import time
import RPi.GPIO as io

start_ts     =  time.time( )
empty_ts     =  start_ts
occupied_ts  =  start_ts

EMPTY     =  0
OCCUPIED  =  1

SECS_UNTIL_EMPTY = 15 # Time until a quad is considered unoccupied

state = EMPTY

pir_pin = 18
led_pin = 25

io.setwarnings( False )

io.setmode( io.BCM )

io.setup( pir_pin, io.IN )
io.setup( led_pin, io.OUT )

def format_state ( state ):
	if state == EMPTY:
		return "EMPTY"
	elif state == OCCUPIED:
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

	if new_state == EMPTY:
		empty_ts  =  now_ts
		light_led( False )
	elif new_state == OCCUPIED:
		occupied_ts  =  now_ts
		light_led( True )
	state  =  new_state


def light_led ( on_or_off ):
	if on_or_off == True:
		io.output( led_pin, io.HIGH )
	else:
		io.output( led_pin, io.LOW )


output( "START" )

try:
	while True:
		now_ts  =  time.time( )
		if io.input( pir_pin ):
			change_state( OCCUPIED )
		elif state == OCCUPIED and ( now_ts - occupied_ts > SECS_UNTIL_EMPTY ):
			change_state( EMPTY )
		time.sleep( 0.5 )
except KeyboardInterrupt:
	light_led( False )
	output( "EXIT" )
	exit( )
