DROP TABLE IF EXISTS state_change;
CREATE TABLE state_change (
	id integer primary key autoincrement,
	state text NOT NULL,
	timestamp integer NOT NULL
);

