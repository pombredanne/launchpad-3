PYTHON_VERSION:=2.6
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
