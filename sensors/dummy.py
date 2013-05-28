import random
import sensor


class DummySensor ( sensor.Sensor ):
	"""Returns a random sensor reading, either in (0,1)"""

	def read ( self ):
		return random.randint( 0, 1 )
