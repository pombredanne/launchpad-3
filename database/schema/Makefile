# Quick hack makefile to (re)create the Launchpad database.
# One day the guts of this will be migrated to Python
#

PYTHON=python2.3

# The development database
DBNAME=launchpad_dev

# A template for databases used by functional tests.
# It is not used directly, but used as a template in a createdb command
# to quickly build a populated database to run tests against.
TEST_DBNAME=launchpad_ftest_template

default: all

# NB. Yes - we run fti.py twice. This should be fixed sometime, but
# it is currently needed to get the fti columns populated correctly.
test: create 
	@ echo "* Loading base database schema"
	@ psql -d ${TEST_DBNAME} -f launchpad-6-00-0.sql | grep : | cat
	@ echo "* Installing tsearch2 into ts2 schema"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py --setup-only
	@ echo "* Patching the database schema"
	@ ls -1 patch*.sql |sort| xargs -n 1 psql -d ${TEST_DBNAME} -q -f | cat
	@ echo "* Setting up full text indexes"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py
	@ echo "* Loading language data"
	@ psql -d ${TEST_DBNAME} -f ../languages.sql | grep : | cat
	@ echo "* Loading sample data"
	@ psql -d ${TEST_DBNAME} -f ../sampledata/current.sql | grep : | cat
	@ echo "* Setting up full text indexes"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py
	@ echo "* Adding comments"
	@ psql -d ${TEST_DBNAME} -f comments.sql | grep : | cat
	@ echo "* Vacuuming"
	@ psql -d ${TEST_DBNAME} -c 'vacuum full analyze' | grep : | cat

empty: create 
	@ echo "* Loading base database schema"
	@ psql -d ${TEST_DBNAME} -f launchpad-6-00-0.sql | grep : | cat
	@ echo "* Installing tsearch2 into ts2 schema"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py --setup-only
	@ echo "* Patching the database schema"
	@ ls -1 patch*.sql |sort| xargs -n 1 psql -d ${TEST_DBNAME} -q -f | cat
	@ echo "* Setting up full text indexes"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py
	@ echo "* Loading language data"
	@ psql -d ${TEST_DBNAME} -f ../languages.sql | grep : | cat
	@ echo "* Setting up full text indexes"
	@ env LP_DBNAME=${TEST_DBNAME} ${PYTHON} fti.py
	@ echo "* Adding comments"
	@ psql -d ${TEST_DBNAME} -f comments.sql | grep : | cat
	@ echo "* Vacuuming"
	@ psql -d ${TEST_DBNAME} -c 'vacuum full analyze' | grep : | cat
	@ echo "* Creating ${DBNAME}"
	@if [ "$$((`psql -l | grep ${DBNAME} | wc -l`))" = '1' ]; \
	    then dropdb ${DBNAME} | grep : | cat ; \
	fi
	@ createdb -E UNICODE --template=${TEST_DBNAME} ${DBNAME} | grep : | cat

dev: test
	@ echo "* Creating ${DBNAME}"
	@if [ "$$((`psql -l | grep ${DBNAME} | wc -l`))" = '1' ]; \
	    then dropdb ${DBNAME} | grep : | cat ; \
	fi
	@ createdb -E UNICODE --template=${TEST_DBNAME} ${DBNAME} | grep : | cat

#testdb: drop create devdb
#	@ echo "* Creating ${TEST_DBNAME} for unittests"
#	@ createdb -E UNICODE --template=${DBNAME} ${TEST_DBNAME} | grep : | cat

create:
	@ echo "* If this fails you need to run as the postgresql superuser"
	@ echo "* eg. sudo -u postgres make create"
	@ echo
	@ echo "* This will hang if another process is accessing the database"
	@ echo
	@if [ "$$((`psql -l | grep ${TEST_DBNAME} | wc -l`))" = '1' ]; \
	    then dropdb ${TEST_DBNAME} | grep : | cat ; \
	fi
	@ echo "* Creating database \"$(TEST_DBNAME)\" with sample data."
	@if [ "$$((`psql -l | grep ${TEST_DBNAME} | wc -l`))" = '0' ]; \
	    then createdb -E UNICODE ${TEST_DBNAME} | grep : | cat ; \
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
	@ psql -d ${TEST_DBNAME} -f trusted.sql | grep : | cat

# Confirm that launchpad-6-00-0.sql hasn't been messed with - this file
# is our baseline telling us what was installed into production
check: search_path
	@if [ "`md5sum launchpad-6-00-0.sql`" != '5f7922451b4619c7d73a4d0cd5bcefaa  launchpad-6-00-0.sql' ]; then echo "* launchpad-6-00-0.sql is corrupt or has been modified"; exit 1; else echo "* Using launchpad-6-00-0 as baseline"; fi

search_path:
	@if [ "`(echo '\t'; echo 'show search_path') | psql -d template1 -q -A -f -`" != "\$$user,public,ts2" ]; then echo "* Add the following to /etc/postgresql/postgresql.conf:"; echo "*   search_path='\$$user,public,ts2'"; echo "* Then reload PostgreSQL:"; echo "*   sudo /etc/init.d/postgresql reload"; exit 1; fi


all: dev test
	@ echo "* All done"

doc:
	${HOME}/Desktop/build/bin/postgresql_autodoc -d ${DBNAME} -f launchpad -t html

newsample-foaf:
	pg_dump -d ${DBNAME} -a -D -O --table=person | grep -v "\(SET \| TOC \)" > ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=emailaddress | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=gpgkey | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=archuserid | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=wikiname | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=jabberid | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=ircid | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=membership | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql
	pg_dump -d ${DBNAME} -a -D -O --table=teamparticipation | grep -v "\(SET \| TOC \)" >> ../sampledata/new-foaf.sql

newsample-doap:
	pg_dump -d ${DBNAME} -a -D -O --table=licence | grep -v "\(SET \| TOC \)" >> ../sampledata/new-doap.sql
	pg_dump -d ${DBNAME} -a -D -O --table=project | grep -v "\(SET \| TOC \)" > ../sampledata/new-doap.sql
	pg_dump -d ${DBNAME} -a -D -O --table=product | grep -v "\(SET \| TOC \)" >> ../sampledata/new-doap.sql
	pg_dump -d ${DBNAME} -a -D -O --table=productseries | grep -v "\(SET \| TOC \)" >> ../sampledata/new-doap.sql
	pg_dump -d ${DBNAME} -a -D -O --table=productrelease | grep -v "\(SET \| TOC \)" >> ../sampledata/new-doap.sql

newsample-rosetta:
	pg_dump -d ${DBNAME} -a -D -O --table=potemplate | grep -v "\(SET \| TOC \)" > ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=pofile | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=pomsgid | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=pomsgset | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=pomsgidsighting | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=potranslation | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql
	pg_dump -d ${DBNAME} -a -D -O --table=potranslationsighting | grep -v "\(SET \| TOC \)" >> ../sampledata/new-rosetta.sql

newsample-soyuz:
	pg_dump -d ${DBNAME} -a -D -O --table=potemplate | grep -v "\(SET \| TOC \)" > ../sampledata/new-rosetta.sql

newsampledata:
	pg_dump --schema=public --disable-triggers -a -D -O -d ${DBNAME} | grep -v "\( TOC \|INSERT INTO \"language\" \|INSERT INTO spokenin \|INSERT INTO country \|INSERT INTO launchpaddatabaserevision \|'language_id_seq\|country_id_seq\|^--\)" > ../sampledata/newsampledata.sql

.PHONY: default base all

