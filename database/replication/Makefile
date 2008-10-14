HERE=`pwd`

LAG=10 seconds

DEV_CONFIG=replicated-development
NEW_STAGING_CONFIG=staging-setup # For building the db with a different name.
STAGING_DUMP=launchpad.dump # Dumpfile to build new staging from.
STAGING_TABLESPACE=launchpad_replication # 'pg_default' for default

_CONFIG=overridden-on-command-line
_SLAVE_TABLESPACE=pg_default

default:
	echo Usage: make [start|stop|restart]

start:
	./slon_ctl.py --lag="${LAG}" start

stop:
	./slon_ctl.py stop

restart: stop start

devsetup:
	make _prelim _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave
	# Build the master database
	LPCONFIG=${DEV_CONFIG} make -C ../schema
	make _replicate _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave

stagingsetup:
	make _prelim _CONFIG=${NEW_STAGING_CONFIG} \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new
	# Create the DB with the desired default tablespace.
	createdb --encoding UTF8 --tablespace ${STAGING_TABLESPACE} \
	    lpmain_staging_new
	# Restore the DB schema.
	pg_restore --dbname=lpmain_staging_new --exit-on-error ${STAGING_DUMP}
	# Uninstall Slony-I if it is installed - a pg_dump of a DB with
	# Slony-I installed isn't usable without this step.
	LPCONFIG=${NEW_STAGING_CONFIG} ./repair-restored-db.py -vv
	# Setup replication
	make _replicate _CONFIG=${NEW_STAGING_CONFIG} \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new \
	    _SLAVE_TABLESPACE=${STAGING_TABLESPACE}

_prelim:
	# Create the slony PostgreSQL superuser if necessary.
	createuser --superuser slony || true
	# Stop the slon daemons and wait a bit for connections to drop.
	LPCONFIG=${_CONFIG} make stop
	sleep 5
	# Drop any existing databases if they exist
	dropdb ${_MASTER} || true
	dropdb ${_SLAVE} || true

_replicate:
	# Create the slave database, empty at this point.
	createdb --encoding=UTF8 --tablespace=${_SLAVE_TABLESPACE} ${_SLAVE}
	# Start the slon daemons with 0 lag for quick setup.
	LPCONFIG=${_CONFIG} make start LAG="0 seconds"
	# Generate a preamble for manual slonik(1) usage.
	LPCONFIG=${_CONFIG} ./preamble.py > preamble.sk
	# Turn the slave into a replica.
	LPCONFIG=${_CONFIG} ./initialize.py
	# Restart slon daemons with default lag setting.
	LPCONFIG=${_CONFIG} make restart LAG="${LAG}"


