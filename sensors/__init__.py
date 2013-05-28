import random

class Sensor:
	"""Encapsulates the logic required to read data from a sensor"""

	def read ( ):
		return None


class DummySensor ( Sensor ):
	"""Returns a random sensor reading, either in (0,1)"""

	def read ( self ):
		return random.randint( 0, 1 )
