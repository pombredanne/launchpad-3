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
	psql -d ${DBNAME} -f launchpad-2-00-0.sql
	@ echo "* Patching the database schema"
	ls -1 patch*.sql | sort | xargs -n 1 psql -d ${DBNAME} -f
#	@ echo "* Loading default data"
#	psql -d ${DBNAME} -f ../default.sql
	@ echo "* Loading language data"
	psql -d ${DBNAME} -f ../languages.sql | cat

# Confirm that launchpad-2-00-0.sql hasn't been messed with - this file
# is our baseline telling us what was installed into production
check:
	@if [ "`md5sum launchpad-2-00-0.sql`" != '33030cf494811a41d7471098414e3f15  launchpad-2-00-0.sql' ]; then echo "* launchpad-2-00-0.sql is corrupt or has been modified"; exit 1; else echo "* Using launchpad-2-00-0 as baseline"; fi

all: base
#	psql -d ${DBNAME} -f ../sampledata/foaf.sql
#	psql -d ${DBNAME} -f ../sampledata/doap.sql
#	psql -d ${DBNAME} -f ../sampledata/soyuz.sql
#	psql -d ${DBNAME} -f ../sampledata/malone.sql
#	psql -d ${DBNAME} -f ../sampledata/rosetta.sql
#	psql -d ${DBNAME} -f ../sampledata/soyuz-extra.sql
	psql -d ${DBNAME} -f ../sampledata/current.sql
	psql -d ${DBNAME} -f comments.sql

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
	pg_dump -d ${DBNAME} -a -D -O | grep -v "\(\SET \| TOC \|INSERT INTO \"language\" \|INSERT INTO spokenin \|INSERT INTO country \|^--\)" > ../sampledata/new-sampledata.sql

.PHONY: default base all

