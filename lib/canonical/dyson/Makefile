SUBDIRS = tests


all:
	for subdir in $(SUBDIRS); do \
		(cd $$subdir && $(MAKE) all) || exit 1; \
	done

check:
	PYTHONPATH=.. python testsuite.py


tags: tags-local tags-recursive

tags-local:
	etags -f ./TAGS *.py

tags-recursive:
	for subdir in $(SUBDIRS); do \
		(cd $$subdir && $(MAKE) tags) || exit 1; \
	done


clean: clean-local clean-recursive

clean-local:
	rm -f *.pyc *~

clean-recursive:
	for subdir in $(SUBDIRS); do \
		(cd $$subdir && $(MAKE) clean) || exit 1; \
	done


.PHONY: all check tags tags-local tags-recursive clean clean-local clean-recursive
