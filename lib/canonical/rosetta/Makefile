
check: tests/test_interfaces_sql.py
	python ../../../test_on_merge.py canonical.rosetta

noisycheck: tests/test_interfaces_sql.py
	(cd ../../.. ; python test.py canonical.rosetta)

testdb:
	make -C ../../../database sampledata

url-table:
	./scripts/extract-urls.py < pages.zcml

tests/test_interfaces_sql.py: interfaces.py sql.py scripts/generate_sql_tests.py
	python scripts/generate_sql_tests.py -c > tests/test_interfaces_sql.py

ftests/test_interfaces_sql.py: interfaces.py sql.py scripts/generate_sql_tests.py
	python scripts/generate_sql_tests.py -o > ftests/test_interfaces_sql.py

clean:
	rm -f tests/test_interfaces_sql.py
	rm -f ftests/test_interfaces_sql.py

sql-tests: tests/test_interfaces_sql.py ftests/test_interfaces_sql.py

.PHONY: check url-table

# arch-tag: 6ffe8e63-5b33-43f6-a70f-c03e6f829162
