# Quick hack makefile to (re)create the Launchpad database.

DBNAME=launchpad_test
TEST_DBNAME=launchpad_unittest_template

default: all

develdb:
	@ echo "* Loading base database schema"
	psql -d ${DBNAME} -f launchpad-3-00-0.sql
	@ echo "* Patching the database schema"
	ls -1 patch*.sql | sort | xargs -n 1 psql -d ${DBNAME} -f
	@ echo "* Loading language data"
	psql -d ${DBNAME} -f ../languages.sql | cat
	@ echo "* Loading sample data"
	psql -d ${DBNAME} -f ../sampledata/current.sql | cat
	@ echo "* Adding comments"
	psql -d ${DBNAME} -f comments.sql | cat

testdb: drop create develdb
	@ echo "* Creating ${TEST_DBNAME} for unittests"
	@if [ "$$((`psql -l | grep ${TEST_DBNAME} | wc -l`))" = '1' ]; \
	    then dropdb ${TEST_DBNAME} ; \
	fi
	createdb -E UNICODE --template=${DBNAME} ${TEST_DBNAME}

create: drop
	@ echo "* If this fails you need to run as the postgresql superuser"
	@ echo "* eg. sudo -u postgres make create"
	@ echo
	@ echo "* This will hang if another process is accessing the database"
	@ echo
	@ echo
	@ echo "* Creating database \"$(DBNAME)\" with sample data."
	@if [ "$$((`psql -l | grep ${DBNAME} | wc -l`))" = '0' ]; \
	    then createdb -E UNICODE ${DBNAME}; \
	    else echo ${DBNAME} already exists; \
         fi
	@ echo
	@ echo "* Installing PL/Python "
	# createlang -d launchpad_test plpythonu
	@ echo
	@ echo "* Creating functions"
	psql -d ${DBNAME} -f trusted.sql

drop: 
	@ echo "* This will hang if another process is accessing the database"
	@ echo "* Dropping existing database"
	@if [ "$$((`psql -l | grep ${DBNAME} | wc -l`))" = '1' ]; then dropdb ${DBNAME} ; fi

# Confirm that launchpad-3-00-0.sql hasn't been messed with - this file
# is our baseline telling us what was installed into production
check:
	@if [ "`md5sum launchpad-3-00-0.sql`" != '4334075ea148a66337de442e9e953d43  launchpad-3-00-0.sql' ]; then echo "* launchpad-3-00-0.sql is corrupt or has been modified"; exit 1; else echo "* Using launchpad-3-00-0 as baseline"; fi

all: drop create develdb testdb
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
	pg_dump -a -D -O -d ${DBNAME} | grep -v "\(\SET \| TOC \|INSERT INTO \"language\" \|INSERT INTO spokenin \|INSERT INTO country \|language_id_seq\|country_id_seq\|^--\)" > ../sampledata/newsampledata.sql

.PHONY: default base all

