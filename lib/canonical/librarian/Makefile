PYTHONVERSION:=
TWISTD:=twistd$(PYTHONVERSION)

PYTHONPATH=../..
pythonpath=PYTHONPATH=$(PYTHONPATH)

default:

tmpdirs=/tmp/fatsam/incoming

$(tmpdirs):
	mkdir -p $@

run: $(tmpdirs)
	$(pythonpath) $(TWISTD) -noy server.tac


.PHONY: default run
