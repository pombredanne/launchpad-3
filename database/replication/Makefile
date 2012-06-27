# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# This makefile is used to build and replicate the staging database.
# To build a replicated development environent, replicate your 9.1 main
# cluster with standard PG 9.1 streaming replication per the PG docs.
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

# For real restores, this is being run on an 8 core system. Let pg_restore
# run multiprocess.
MULTIPROC=-j 4

NEW_STAGING_CONFIG=staging-setup # For building the db with a different name.
STAGING_CONFIG=staging-db # For swapping fresh db into place.
STAGING_DUMP=launchpad.dump # Dumpfile to build new staging from.
STAGING_TABLESPACE=pg_default # 'pg_default' for default
STAGING_LOGDIR=/srv/staging.launchpad.net/staging-logs
DOGFOOD_DBNAME=launchpad_dogfood
DOGFOOD_DUMP=launchpad.dump

PGMASSACRE=../../utilities/pgmassacre.py

CREATEDB=createdb --encoding=UTF8 --locale=C --template=template0

# Turn off output silencing so we can see details of staging deployments.
# Without the timestamps, we are unable to estimate production deployment
# times.
#SHHH=../../utilities/shhh.py
SHHH=

default:
	echo Need a target

# Destroy the existing staging db and reload it from dump. We no longer
# have enough disk space to build it in a holding area and swap it into
# place.
stagingsetup:
	-${PGMASSACRE} lpmain_staging
	# Create the DB with the desired default tablespace.
	${CREATEDB} --tablespace ${STAGING_TABLESPACE} lpmain_staging
	# Restore the database. We need to restore permissions, despite
	# later running security.py, to pull in permissions granted on
	# production to users not maintained by security.py.
	pg_restore --dbname=lpmain_staging ${EXIT_ON_ERROR} \
	    ${MULTIPROC} ${STAGING_DUMP}
	# Apply database patches.
	@echo Running upgrade.py `date`.
	LPCONFIG=${STAGING_CONFIG} ${SHHH} ../schema/upgrade.py \
	    --ignore-slony --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log
	@echo Running security.py `date`
	LPCONFIG=${STAGING_CONFIG} ${SHHH} ../schema/security.py \
	    --log-file=INFO:${STAGING_LOGDIR}/dbupgrade.log

# Switch the _new staging databases into place.
stagingswitch:
	echo Nothing to do. Staging already built inplace.

dogfood:
	${CREATEDB} ${DOGFOOD_DBNAME}
	pg_restore --dbname=${DOGFOOD_DBNAME} --no-acl --no-owner \
	    ${EXIT_ON_ERROR} ${DOGFOOD_DUMP}
	../schema/upgrade.py --ignore-slony -d ${DOGFOOD_DBNAME}
	../schema/security.py -d ${DOGFOOD_DBNAME}
