
# The -u argument disables all functional tests.

check: tests/test_interfaces_sql.py
	python ../../../test_on_merge.py -u canonical.rosetta

.PHONY: check

noisycheck: tests/test_interfaces_sql.py
	(cd ../../.. ; python test.py -u canonical.rosetta)

.PHONY: noisycheck

fullcheck: sql-tests
	(cd ../../.. ; python test.py canonical.rosetta)

.PHONY: fullcheck

testdb:
	#dropdb launchpad_test
	make -C ../../../database/schema

.PHONY: testdb

url-table:
	./scripts/extract-urls.py < pages.zcml

.PHONY: url-table

tests/test_interfaces_sql.py: interfaces.py scripts/generate_sql_tests.py
#	python scripts/generate_sql_tests.py -c > tests/test_interfaces_sql.py

ftests/test_interfaces_sql.py: interfaces.py scripts/generate_sql_tests.py
#	python scripts/generate_sql_tests.py -o > ftests/test_interfaces_sql.py

clean:
	rm -f tests/test_interfaces_sql.py
	rm -f ftests/test_interfaces_sql.py

.PHONY: clean

sql-tests: tests/test_interfaces_sql.py ftests/test_interfaces_sql.py

.PHONY: sql-tests

# arch-tag: 6ffe8e63-5b33-43f6-a70f-c03e6f829162
