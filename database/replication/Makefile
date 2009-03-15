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
	./slon_ctl.py stop

restart: stop start

devsetup:
	make _prelim _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave
	# Build the master database
	LPCONFIG=${DEV_CONFIG} make -C ../schema
	make _replicate _CONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave

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
	LPCONFIG=${NEW_STAGING_CONFIG} ../schema/security.py \
		 -d lpmain_staging_slave_new -U slony

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
	createuser --superuser slony || true
	# Stop the slon daemons and wait a bit for connections to drop.
	LPCONFIG=${_CONFIG} make stop
	sleep 5
	# Drop any existing databases if they exist
	${PGMASSACRE} ${_MASTER}
	${PGMASSACRE} ${_SLAVE}

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


