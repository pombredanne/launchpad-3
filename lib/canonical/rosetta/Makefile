check:
	python ../../../test_on_merge.py canonical.rosetta

noisycheck:
	(cd ../../.. ; python test.py canonical.rosetta)

testdb:
	make -C ../../../database sampledata

url-table:
	./scripts/extract-urls.py < pages.zcml

generate-sql-tests:
	python scripts/generate_sql_tests.py -c >  tests/test_interfaces_sql.py
	python scripts/generate_sql_tests.py -o > ftests/test_interfaces_sql.py

.PHONY: check url-table

# arch-tag: 6ffe8e63-5b33-43f6-a70f-c03e6f829162
