# Quick hack makefile to recreate launchpad_test

DBNAME=launchpad_test

default: all

base:
	@ echo "* Creating database \"$(DBNAME)\" with sample data."
	@ echo "* This will hang if another process is accessing the database"
	createdb -E UNICODE launchpad_test || echo ${DBNAME} already exists
	psql -d ${DBNAME} -f launchpad-1-0-0.sql
	ls -1 patch*.sql | sort | xargs -n 1 psql -d ${DBNAME} -f
	psql -d ${DBNAME} -f ../default.sql
	 # 2004-09-09: languages.sql puts you into more. Quite annoying.
	 # If stdout is not a tty it behaves better. 
	psql -d ${DBNAME} -f ../languages.sql | cat

all: base
	psql -d ${DBNAME} -f ../sampledata.sql
	psql -d ${DBNAME} -f ../sampledata-soyuz.sql
	psql -d ${DBNAME} -f ../sampledata-malone.sql
	psql -d ${DBNAME} -f ../sampledata-rosetta.sql
	psql -d ${DBNAME} -f comments.sql


.PHONY: default base all
