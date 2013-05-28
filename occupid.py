from daemon import runner
from occupi import *

class OccupiDaemon:

	def __init__ ( self ):
		# Daemon-related atttributes
		self.stdin_path       =  '/dev/null'
		self.stdout_path      =  '/dev/null'
		self.stderr_path      =  '/dev/null'
		self.pidfile_path     =  PID_FILE_PATH
		self.pidfile_timeout  =  5


	def run ( self ):
		occupi  =  Occupi( )
		occupi.run( )


if __name__ == '__main__':
	occupid  =  OccupiDaemon( )
	daemon_runner  =  runner.DaemonRunner( occupid )
	daemon_runner.do_action( )
