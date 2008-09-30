HERE=`pwd`

DEVCONFIG=replicated-development

default:
	echo Usage: make [start|stop|restart]

start:
	LPCONFIG=${DEVCONFIG} ./slon_ctl.py start

stop:
	LPCONFIG=${DEVCONFIG} ./slon_ctl.py stop

restart: stop start

devsetup:
	# Create the slony PostgreSQL superuser if necessary.
	createuser --superuser slony || true
	# Stop the slon daemons and wait a bit for connections to drop.
	LPCONFIG=${DEVCONFIG} make stop
	sleep 5
	# Drop any existing databases if they exist
	dropdb launchpad_dev || true
	dropdb launchpad_dev_slave1 || true
	# Build the master database
	LPCONFIG=${DEVCONFIG} make -C ../schema
	# Create the slave database, empty at this point.
	createdb --encoding=UTF8 launchpad_dev_slave1
	# Start the slon daemons
	LPCONFIG=${DEVCONFIG} make start
	# Generate a preamble for manual slonik(1) usage.
	LPCONFIG=${DEVCONFIG} ./preamble.py > preamble.sk
	# Turn the slave into a replica
	LPCONFIG=${DEVCONFIG} ./initialize.py

