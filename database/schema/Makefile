# Quick hack makefile to (re)create the Launchpad database.
# One day the guts of this will be migrated to Python
#

PYTHON=python2.4

# The database dump to restore on database creation
SAMPLEDATA=../sampledata/current.sql

# The database dump to create
NEWSAMPLEDATA=../sampledata/newsampledata.sql

# The development database
DBNAME=launchpad_dev

# A template for databases used by functional tests.
# It is not used directly, but used as a template in a createdb command
# to quickly build a populated database to run tests against.
TEST_DBNAME=launchpad_ftest_template
EMPTY_DBNAME=launchpad_empty

# The session database name.
SESSION_DBNAME=session_dev

# The command we use to drop a database
DROPDB=${PYTHON} ../../utilities/pgmassacre.py
# The command we use to create a database
CREATEDB=${PYTHON} ../../utilities/pgcreate.py

# The latest schema dump from production. Database patches are relative
# to this baseline. This dump should be updated every production rollout
# to ensure that the development database remains in sync with reality
# on production. It is generated using newbaseline.py in
# sftp://chinstrap/home/warthogs/archives/stub/dbascripts:
# 
REV=88
BASELINE=launchpad-${REV}-00-0.sql
MD5SUM=302fc5e82034698775098ae47b6846bc  launchpad-88-00-0.sql
default: all

test: create 
	@ echo "* Installing tsearch2 into ts2 schema"
	@ ${PYTHON} fti.py -q --setup-only -d ${TEST_DBNAME}
	@ echo "* Loading base database schema"
	@ psql -d ${TEST_DBNAME} -f ${BASELINE} | grep : | cat
	@ echo "* Patching the database schema"
	@ ${PYTHON} upgrade.py -d ${TEST_DBNAME}
	@ echo "* Setting up full text indexes"
	@ ${PYTHON} fti.py -q -d ${TEST_DBNAME}
	@ echo "* Security setup"
	@ ${PYTHON} security.py -d ${TEST_DBNAME}
	@ echo "* Creating database \"$(EMPTY_DBNAME)\" with no sample data."
	@ sleep 2
	@ ${CREATEDB} ${TEST_DBNAME} ${EMPTY_DBNAME}
	@ echo "* Loading sample data"
	@ psql -v ON_ERROR_STOP=1 -d ${TEST_DBNAME} -f $(SAMPLEDATA) > /dev/null
	@ echo "* Rebuilding full text indexes"
	@ ${PYTHON} fti.py --force -q -d ${EMPTY_DBNAME}
	@ ${PYTHON} fti.py --force -q -d ${TEST_DBNAME}
	@ echo "* Resetting sequences"
	@ ${PYTHON} reset_sequences.py -d ${TEST_DBNAME}
	@ echo "* Vacuuming"
	@ psql -d ${TEST_DBNAME} -c 'vacuum full analyze' | grep : | cat
	@ echo "* Creating session database '${SESSION_DBNAME}' (if necessary)"
	@if [ "$$((`psql -l | grep ${SESSION_DBNAME} | wc -l`))" = '0' ]; \
	    then ${CREATEDB} template1 ${SESSION_DBNAME} ; \
	    createlang plpgsql ${SESSION_DBNAME}; \
	    psql -q -d ${SESSION_DBNAME} -f launchpad_session.sql ; \
	fi
	@ echo "* Adding session tables to '${TEST_DBNAME}'"
	psql -q -d ${TEST_DBNAME} -f launchpad_session.sql

dev: test
	@ echo "* Creating ${DBNAME}"
	@if [ "$$((`psql -l | grep ${DBNAME} | wc -l`))" = '1' ]; \
	    then ${DROPDB} ${DBNAME} | grep : | cat ; \
	fi
	@ sleep 2
	@ ${CREATEDB} ${TEST_DBNAME} ${DBNAME}

create: check
	@ echo "* If this fails you need to run as the postgresql superuser"
	@ echo "* eg. sudo -u postgres make create"
	@ echo
	@if [ "$$((`psql -l | grep ${TEST_DBNAME} | wc -l`))" = '1' ]; \
	    then ${DROPDB} ${TEST_DBNAME} | grep : | cat ; \
	fi
	@if [ "$$((`psql -l | grep ${EMPTY_DBNAME} | wc -l`))" = '1' ]; \
	    then ${DROPDB} ${EMPTY_DBNAME} | grep : | cat ; \
	fi
	@ echo "* Creating database \"$(TEST_DBNAME)\" with sample data."
	@if [ "$$((`psql -l | grep ${TEST_DBNAME} | wc -l`))" = '0' ]; \
	    then ${CREATEDB} template1 ${TEST_DBNAME} ; \
	    else echo ${TEST_DBNAME} already exists; \
	fi
	@ if ! `createlang -l ${TEST_DBNAME} | grep -qs plpythonu`; then \
		echo "* Installing PL/PythonU"; \
		createlang -d ${TEST_DBNAME} plpythonu; \
	fi
	@ if ! `createlang -l ${TEST_DBNAME} | grep -qs plpgsql`; then \
		echo "* Installing PL/PgSQL"; \
	    	createlang -d ${TEST_DBNAME} plpgsql; \
	fi
	@ echo "* Creating functions"
	@ psql -d ${TEST_DBNAME} -f trusted.sql   | grep : | cat
	@ psql -d ${TEST_DBNAME} -f testfuncs.sql | grep : | cat

# Confirm that launchpad-XX-00-0.sql hasn't been messed with - this file
# is our baseline telling us what was installed into production
check: search_path
	@if [ "`md5sum ${BASELINE}`" != "${MD5SUM}" ]; then echo "* ${BASELINE} is corrupt or has been modified"; exit 1; else echo "* Using ${BASELINE} as baseline"; fi

search_path:
	@psql -d template1 -q -A -t -c 'show search_path'
	@if [ `psql -d template1 -q -A -t -c 'show search_path'` != '$$user,public,ts2' ]; then \
		echo "* It appears your search path is unconfigured."; \
		echo "	Have you read <https://launchpad.canonical.com/DatabaseSetup>?";  \
		echo; \
		echo "* Add the following to /etc/postgresql/8.1/main/postgresql.conf:"; \
		echo "    search_path='\$$user,public,ts2'"; \
		echo "* Then reload PostgreSQL:";  \
		echo "    sudo /etc/init.d/postgresql reload";  \
		exit 1; \
	 fi


all: dev test
	@ echo "* All done"

doc:
	postgresql_autodoc -d ${DBNAME} -f launchpad -t html
	tidy -asxhtml launchpad.html > ,launchpad.html || mv ,launchpad.html launchpad.html

diagram:
	${PYTHON} diagram.py

newsampledata:
	$(PYTHON) fti.py --null -d launchpad_dev -q
	pg_dump --schema=public --disable-triggers -a -D -O -d ${DBNAME} \
	| grep -v "\( TOC \|INSERT INTO launchpaddatabaserevision \|sessiondata\|sessionpkgdata\|secret\|SELECT pg_catalog\.setval\|^--\| fticache \|'fticache'\)" \
	| $(PYTHON) sort_sql.py \
	> $(NEWSAMPLEDATA)
	$(PYTHON) fti.py --force -d launchpad_dev -q

.PHONY: default base all

