# Quick hack makefile to recreate launchpad_test
#

DBNAME=launchpad_test

launchpad_test: .FORCE
	@ echo This will hang if another process is accessing the database
	createdb -E UNICODE launchpad_test || echo ${DBNAME} already exists
	ls -1 *.sql | sort | xargs -n 1 psql -d ${DBNAME} -f 2>&1 \
	    | grep -v NOTICE:
	psql -d ${DBNAME} -f ../default.sql
	psql -d ${DBNAME} -f ../languages.sql
	psql -d ${DBNAME} -f ../sampledata.sql
	psql -d ${DBNAME} -f ../sampledata-rosetta.sql

.FORCE:

