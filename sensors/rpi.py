import RPi.GPIO as io


class PIRSensor ( Sensor ):
	"""Reads from an RPi GPIO pin connected to a PIR breakout board"""

	def __init__ ( self, pin ):
		self.pin  =  pin
		io.setup( pin, io.IN )

	def read ( self ):
		return io.input( self.pin )
