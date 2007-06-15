# Copyright 2007 Canonical Ltd.  All rights reserved.

all: deb

deb: clean
	dpkg-buildpackage -rfakeroot -b

clean:
	fakeroot debian/rules clean
	rm -f launchpad-buildd*deb
	rm -f ../launchpad-buildd*changes

.PHONY: all clean deb
