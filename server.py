from __future__ import with_statement
from flask      import Flask, _app_ctx_stack, jsonify
from sqlite3    import dbapi2 as sqlite3

DATABASE  =  './occupi.db'
DEBUG = True

# Set up Flask
app = Flask( __name__ )

@app.route('/')
def get_state ( ):
	return jsonify( { 'occupied': 0 } )

def init_db ( ):
	with app.app_context( ):
		db  =  get_db
		with app.open_resource( 'schema.sql' ) as f:
			db.cursor( ).executescript( f.read( ) )
		db.commit( )

def get_db ( ):
	top  =  _app_ctx_stack
	if not hasattr( top, 'sqlite_db' ):
		sqlite_db  =  sqlite3.connect( app.config['DATABASE'] )
		sqlite_db.row_factory  =  sqlite3.Row
		top.sqlite_db  =  sqlite_db

	return top.sqlite_db

if __name__ == '__main__':
	app.run( debug=True, host='0.0.0.0' )
