HERE=`pwd`

LAG=10 seconds

DEV_CONFIG=replicated-development
NEW_STAGING_CONFIG=staging-setup # For building the db with a different name.
STAGING_CONFIG=staging # For swapping fresh db into place.
STAGING_DUMP=launchpad.dump # Dumpfile to build new staging from.
STAGING_TABLESPACE=pg_default # 'pg_default' for default

_CONFIG=overridden-on-command-line
_SLAVE_TABLESPACE=pg_default

PGMASSACRE=../../utilities/pgmassacre.py

default:
	echo Usage: make [start|stop|restart]

start:
	./slon_ctl.py --lag="${LAG}" start

stop:
	-./slon_ctl.py stop

restart: stop start

devsetup:
	make _prelim _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave
	# Build the master database
	LPCONFIG=${DEV_CONFIG} make -C ../schema
	# Replicate it
	make _replicate _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave LAG="0 seconds"

	# Add a new slave to the existant cluster
	##LPCONFIG=${DEV_CONFIG} ./new-slave.py "dbname=launchpad_dev_slave2"
	# Regenerate our preamble for the new slave
	##LPCONFIG=${DEV_CONFIG} ./preamble.py > preamble.sk
	# Restart slon daemons with lag setting
	##LPCONFIG=${DEV_CONFIG} make restart LAG="${LAG}"

# Build _new staging databases from a production dump.
stagingsetup:
	make _prelim _CONFIG=${NEW_STAGING_CONFIG} \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new
	# Create the DB with the desired default tablespace.
	createdb --encoding UTF8 --tablespace ${STAGING_TABLESPACE} \
	    lpmain_staging_new
	# Restore the DB schema. Don't restore permissions - it will blow
	# up when roles don't exist in this cluster, and we rebuild it later
	# with security.py anyway.
	pg_restore --dbname=lpmain_staging_new \
	    --no-acl --exit-on-error ${STAGING_DUMP}
	# Uninstall Slony-I if it is installed - a pg_dump of a DB with
	# Slony-I installed isn't usable without this step.
	LPCONFIG=${NEW_STAGING_CONFIG} ./repair-restored-db.py
	# Analyze the new db performance doesn't suck until autovacuum
	# gets around to it. This can be done in the background while
	# the slave is being rebuilt, but needs to start *after* the
	# subscription has started to avoid the open transaction blocking
	# the setup. slon automatically analyzes newly
	# replicated tables on the slave, so no need to analyze the slave
	# ourselves.
	(sleep 900; psql -d lpmain_staging_new -c 'analyze;') &
	# Setup replication
	make _replicate _CONFIG=${NEW_STAGING_CONFIG} LAG="0 seconds" \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new \
	    _SLAVE_TABLESPACE=${STAGING_TABLESPACE}
	# Upgrade the _new databases and rebuild acls.
	LPCONFIG=${NEW_STAGING_CONFIG} ../schema/upgrade.py
	LPCONFIG=${NEW_STAGING_CONFIG} ../schema/fti.py
	LPCONFIG=${NEW_STAGING_CONFIG} ../schema/security.py \
		 -d lpmain_staging_new -U slony

# Switch the _new staging databases into place.
stagingswitch:
	# Stop Slony-I daemons - don't confuse the poor darlings.
	make stop LPCONFIG=${NEW_STAGING_CONFIG}
	make stop LPCONFIG=${STAGING_CONFIG}
	# Kill the existing staging database if it exists.
	${PGMASSACRE} lpmain_staging
	${PGMASSACRE} lpmain_staging_slave
	# Rename the newly build staging databases.
	psql -d template1 -c \
	    "ALTER DATABASE lpmain_staging_new RENAME TO lpmain_staging;"
	psql -d template1 -c "\
	    ALTER DATABASE lpmain_staging_slave_new \
	    RENAME TO lpmain_staging_slave;"
	# Generate a suitable preamble, now using the real staging config.
	LPCONFIG=${STAGING_CONFIG} ./preamble.py > preamble.sk
	# Change the paths between the nodes to match what they will be soon.
	echo "\
	include <preamble.sk>; 				\
	store path ( 					\
	    server = @master_node, client=@slave1_node,	\
	    conninfo=@master_conninfo);			\
	store path (					\
	    server = @slave1_node, client=@master_node,	\
	    conninfo=@slave1_conninfo);			\
	" | slonik
	make start LPCONFIG=${STAGING_CONFIG}

_prelim:
	# Create the slony PostgreSQL superuser if necessary.
	-createuser --superuser slony
	# Stop the slon daemons and wait a bit for connections to drop.
	LPCONFIG=${_CONFIG} make stop
	sleep 5
	# Drop any existing databases if they exist
	${PGMASSACRE} ${_MASTER}
	${PGMASSACRE} ${_SLAVE}

_replicate:
	# Start the slon daemon for the master.
	LPCONFIG=${_CONFIG} ./slon_ctl.py start \
		 node1_node 'dbname=launchpad_dev user=slony'
	
	# Initialize the cluster and create replication sets.
	LPCONFIG=${_CONFIG} ./initialize.py -vv

	# Start the slon daemon for the slave
	LPCONFIG=${_CONFIG} ./slon_ctl.py start \
		 node2_node 'dbname=launchpad_dev_slave user=slony'

	# Create the soon-to-be-slave database, empty at this point.
	createdb --encoding=UTF8 --tablespace=${_SLAVE_TABLESPACE} ${_SLAVE}

	# Duplicate the schema of the master
	pg_dump -U postgres --schema-only --no-privileges ${_MASTER} \
	    | psql -1 -q -U postgres -d ${_SLAVE}
	-psql -1 -q -U postgres -d ${_SLAVE} -c 'DROP SCHEMA _sl CASCADE' \
	    2>&1 | grep -v 'NOTICE:  drop cascades'

	# Setup the slave
	LPCONFIG=${_CONFIG} ./new-slave.py 2 "dbname=${_SLAVE}"

	# Restart slon daemons with default lag setting.
	LPCONFIG=${_CONFIG} make restart LAG="${LAG}"

	# Generate a preamble for manual slonik(1) usage.
	LPCONFIG=${_CONFIG} ./preamble.py > preamble.sk


