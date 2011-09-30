# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# This makefile is used for two task:
#
#  - Build a replicated development environment
#  - Build and replicate the staging database
#
# To build a replicated development environment:
#
#  $ make -C database/replication devsetup
#  $ make run
#
# To test the staging rebuild script:
#
#  $ mkdir -p /srv/staging.launchpad.net/staging-logs
#  $ cd database/replication
#  $ pg_dump --format=c launchpad_dev > launchpad.dump
#  $ make stagingsetup \
#        STAGING_CONFIG=dev-staging STAGING_DUMP=launchpad.dump
#  $ make stagingswitch STAGING_CONFIG=dev-staging
#
# To restore a dogfood database:
#
#  $ cd database/replication
#  $ make dogfood DOGFOOD_DBNAME=launchpad_dogfood DOGFOOD_DUMP=launchpad.dump
#

# This used to be 10 seconds, so we always ran staging lagged to detect
# replication glitches more easily. However, this does not play well
# with DBLoopTuner, as it correctly blocks when it detects lag.
# We should put this back when DBLoopTuner is more intelligent, perhaps
# pulling the allowable lag setting from a config file.
LAG=0 seconds

# For real restores, this is being run on an 8 core system. Let pg_restore
# run multiprocess.
MULTIPROC=-j 4

DEV_CONFIG=replicated-development
NEW_STAGING_CONFIG=staging-setup # For building the db with a different name.
STAGING_CONFIG=staging-db # For swapping fresh db into place.
STAGING_DUMP=launchpad.dump # Dumpfile to build new staging from.
STAGING_TABLESPACE=pg_default # 'pg_default' for default
STAGING_LOGDIR=/srv/staging.launchpad.net/staging-logs
DOGFOOD_DBNAME=launchpad_dogfood
DOGFOOD_DUMP=launchpad.dump

_CONFIG=overridden-on-command-line
_SLAVE_TABLESPACE=pg_default

PGMASSACRE=../../utilities/pgmassacre.py

CREATEDB_83=createdb --encoding=UTF8
CREATEDB_84=createdb --encoding=UTF8 --locale=C --template=template0
CREATEDB=${CREATEDB_84}

# Set this to --exit-on-error once our dumps are coming from a PG 8.4
# source. Currently, the PG 8.3 dumps generate some spurious errors
# when being restored into a PG 8.4 database.
EXIT_ON_ERROR=--exit-on-error

# Turn off output silencing so we can see details of staging deployments.
# Without the timestamps, we are unable to estimate production deployment
# times.
#SHHH=../../utilities/shhh.py
SHHH=

default:
	echo Usage: make [start|stop|restart]

start:
	./slon_ctl.py --lag="${LAG}" start

stop:
	./slon_ctl.py stop

restart: stop start

devsetup:
	make _prelim LPCONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave LAG="0 seconds"
	
	# Build the master database
	LPCONFIG=${DEV_CONFIG} make -C ../schema
	
	# Replicate it
	make _replicate LPCONFIG=${DEV_CONFIG} \
	    _MASTER=launchpad_dev _SLAVE=launchpad_dev_slave LAG="0 seconds"
	
	# Replicate it again, so we can test with multiple slaves.
	-${PGMASSACRE} launchpad_dev_slave2
	${CREATEDB} launchpad_dev_slave2
	LPCONFIG=${DEV_CONFIG} ./slon_ctl.py start \
		 node3_node 'dbname=launchpad_dev_slave2 user=slony'
	LPCONFIG=${DEV_CONFIG} ./new-slave.py 3 launchpad_dev_slave2
	LPCONFIG=${DEV_CONFIG} ../schema/security.py -d launchpad_dev_slave2
	
	# Regenerate the preamble for manual slonik(1) usage.
	LPCONFIG=${DEV_CONFIG} ./preamble.py > preamble.sk

	# Restart slon daemons with default lag setting.
	LPCONFIG=${DEV_CONFIG} ./slon_ctl.py stop
	LPCONFIG=${DEV_CONFIG} ./slon_ctl.py --lag="${LAG}" start


# Build _new staging databases from a production dump.
stagingsetup:
	make _prelim LPCONFIG=${NEW_STAGING_CONFIG} \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new \
	    LAG="0 seconds"
	# Create the DB with the desired default tablespace.
	${CREATEDB} --tablespace ${STAGING_TABLESPACE} lpmain_staging_new
	# Restore the database. We need to restore permissions, despite
	# later running security.py, to pull in permissions granted on
	# production to users not maintained by security.py.
	pg_restore --dbname=lpmain_staging_new --no-owner ${EXIT_ON_ERROR} \
	    ${MULTIPROC} ${STAGING_DUMP}
	# Uninstall Slony-I if it is installed - a pg_dump of a DB with
	# Slony-I installed isn't usable without this step.
	LPCONFIG=${NEW_STAGING_CONFIG} ./repair-restored-db.py
	# Setup replication
	make _replicate LPCONFIG=${NEW_STAGING_CONFIG} LAG="0 seconds" \
	    _MASTER=lpmain_staging_new _SLAVE=lpmain_staging_slave_new \
	    _SLAVE_TABLESPACE=${STAGING_TABLESPACE}

# Switch the _new staging databases into place.
stagingswitch:
	# Stop Slony-I daemons - don't confuse the poor darlings.
	-LPCONFIG=${NEW_STAGING_CONFIG} ./slon_ctl.py stop
	-LPCONFIG=${STAGING_CONFIG} ./slon_ctl.py stop
	# Kill the existing staging database if it exists.
	-${PGMASSACRE} lpmain_staging
	-${PGMASSACRE} lpmain_staging_slave
	# Rename the newly build staging databases.
	psql -d template1 -c \
	    "ALTER DATABASE lpmain_staging_new RENAME TO lpmain_staging;"
	psql -d template1 -c "\
	    ALTER DATABASE lpmain_staging_slave_new \
	    RENAME TO lpmain_staging_slave;"
	# Fix the paths to match.
	psql -d lpmain_staging -U slony -c \
	"UPDATE _sl.sl_path SET pa_conninfo=replace(pa_conninfo, '_new', '')"
	psql -d lpmain_staging_slave -U slony -c \
	"UPDATE _sl.sl_path SET pa_conninfo=replace(pa_conninfo, '_new', '')"
	# Start the slon daemons, with requested lag.
	LPCONFIG=${STAGING_CONFIG} ./slon_ctl.py --lag="${LAG}" start

dogfood:
	${CREATEDB} ${DOGFOOD_DBNAME}
	# Stop ignoring error code after are dumps come from an 8.4 system.
	-pg_restore --dbname=${DOGFOOD_DBNAME} --no-acl --no-owner \
	    ${EXIT_ON_ERROR} ${DOGFOOD_DUMP}
	./repair-restored-db.py -d ${DOGFOOD_DBNAME}
	../schema/upgrade.py -d ${DOGFOOD_DBNAME}
	../schema/fti.py -d ${DOGFOOD_DBNAME}
	../schema/security.py -d ${DOGFOOD_DBNAME}

_prelim:
	@echo LPCONFIG currently ${LPCONFIG}
	# Create the slony PostgreSQL superuser if necessary.
	-createuser --superuser slony
	# Stop the slon daemons and wait a bit for connections to drop.
	-./slon_ctl.py stop
	sleep 5
	# Drop any existing databases if they exist
	${PGMASSACRE} ${_MASTER}
	${PGMASSACRE} ${_SLAVE}

_replicate:
	@echo LPCONFIG currently ${LPCONFIG}
	# Start the slon daemon for the master.
	./slon_ctl.py --lag="0 seconds" start \
		 node1_node "dbname=${_MASTER} user=slony"
	# Initialize the cluster and create replication sets.
	./initialize.py \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	# Create the soon-to-be-slave database, empty at this point.
	${CREATEDB} --tablespace=${_SLAVE_TABLESPACE} ${_SLAVE}
	# Start the slon daemon for the slave
	./slon_ctl.py --lag="0 seconds" start \
	    node2_node "dbname=${_SLAVE} user=slony"
	# Setup the slave
	./new-slave.py 2 "dbname=${_SLAVE}" \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	# Upgrade all databases in the cluster and reset security.
	@echo Running upgrade.py `date`
	${SHHH} ../schema/upgrade.py \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	@echo Running fti.py `date`
	${SHHH} ../schema/fti.py \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	@echo Running security.py `date`
	./slon_ctl.py stop # security.py can deadlock with slony
	${SHHH} ../schema/security.py --cluster -U slony \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	# Restart slon daemons with default lag setting.
	./slon_ctl.py --lag="${LAG}" start
	# Generate a preamble for manual slonik(1) usage.
	./preamble.py > preamble.sk

