# Quick hack makefile to (re)create the Launchpad database.

DBNAME=launchpad_test

default: all

# 2004-09-09: languages.sql puts you into more. Quite annoying.
# If stdout is not a tty it behaves better.
base: check
	@ echo "* Creating database \"$(DBNAME)\" with sample data."
	@ echo "* This will hang if another process is accessing the database"
	createdb -E UNICODE ${DBNAME} || echo ${DBNAME} already exists
	@ echo "* Loading base database schema"
	psql -d ${DBNAME} -f launchpad-1-0-0.sql
	@ echo "* Patching the database schema"
	ls -1 patch*.sql | sort | xargs -n 1 psql -d ${DBNAME} -f
	@ echo "* Loading default data"
	psql -d ${DBNAME} -f ../default.sql
	@ echo "* Loading language data"
	psql -d ${DBNAME} -f ../languages.sql | cat

# Confirm that launchpad-1-0-0.sql hasn't been messed with - this file
# is our baseline telling us what was installed into production
check:
	@if [ "`md5sum launchpad-1-0-0.sql`" != 'c87da6b7742ffd520fc612334ccba7f0  launchpad-1-0-0.sql' ]; then echo "* launchpad-1-0-0.sql is corrupt or has been modified"; exit 1; else echo "* Using launchpad-1-0-0 as baseline"; fi

all: base
	psql -d ${DBNAME} -f ../sampledata.sql
	psql -d ${DBNAME} -f ../sampledata-soyuz.sql
	psql -d ${DBNAME} -f ../sampledata-malone.sql
	psql -d ${DBNAME} -f ../sampledata-rosetta.sql
	psql -d ${DBNAME} -f comments.sql

.PHONY: default base all

