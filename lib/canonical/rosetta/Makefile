check:
	python ../../../test_on_merge.py canonical.rosetta

noisycheck:
	(cd ../../.. ; python test.py canonical.rosetta)

url-table:
	./scripts/extract-urls.py < pages.zcml

.PHONY: check url-table

# arch-tag: 6ffe8e63-5b33-43f6-a70f-c03e6f829162
