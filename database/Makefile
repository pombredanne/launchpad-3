# arch-tag: 6773f9cf-f527-48bb-8521-7a103f106633
# (c) 2004  Canonical Software Ltd
# David Allouche: okay, that's quite possibly crack, feel free to remove


default:
	@ echo "Usage: $(MAKE) TARGET"
	@ echo
	@ echo "  launchpad   create and populate the launchpad database"
	@ echo "  launchpad_test  create and populate the test database"

+postgres:
	@ if ! which postgresql ; then \
	echo "* install postgres" ; \
	echo "sudo apt-get install postgresql" ; \
	sudo apt-get install postgresql ; fi
	touch $@

+pguser: +postgres
	@ echo '* make sure your user has write access' \
	'to a database called "launchpad"'
	 # pass through root to sudo to postgres
	sudo sudo -u postgres createuser -A -d $$(id -un)
	id -un > $@

+launchpad-db: +pguser
	@ echo '* create the database'
	createdb launchpad
	touch $@

launchpad: +launchpad-db
	@ echo '* create the database tables'
	psql --file launchpad.sql launchpad
	@ echo '* populate it with the schema information'
	psql --file schemas.sql launchpad

+launchpad_test-db: +pguser
	@ echo '* create the database'
	createdb launchpad_test
	touch $@

launchpad_test: +launchpad_test-db
	@ echo '* create the database tables'
	psql --file launchpad.sql launchpad_test
	@ echo '* populate it with the schema information'
	psql --file schemas.sql launchpad_test

.PHONY: default launchpad launchpad_test
