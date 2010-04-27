# XXX: Nasty hack to make sure the default python is used when
# building/running.
PYTHON_VERSION:=$(shell python -c 'import sys; print ".".join(["%d" % n for n in sys.version_info[:2]])')
TWISTD:=twistd$(PYTHON_VERSION)

PYTHONPATH=../..
pythonpath=PYTHONPATH=$(PYTHONPATH)

default:

tmpdirs=/tmp/fatsam/incoming

$(tmpdirs):
	mkdir -p $@

run: $(tmpdirs)
	$(pythonpath) $(TWISTD) -noy server.tac


.PHONY: default run
