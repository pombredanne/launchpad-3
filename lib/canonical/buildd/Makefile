# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

all: deb

src: clean
	dpkg-buildpackage -rfakeroot -uc -us -S

deb: clean
	dpkg-buildpackage -rfakeroot -uc -us

clean:
	fakeroot debian/rules clean
	rm -f ../launchpad-buildd*tar.gz
	rm -f ../launchpad-buildd*dsc
	rm -f ../launchpad-buildd*deb
	rm -f ../launchpad-buildd*changes

.PHONY: all clean deb
