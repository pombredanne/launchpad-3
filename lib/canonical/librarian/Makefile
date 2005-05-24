PYTHON_VERSION:=2.4
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
