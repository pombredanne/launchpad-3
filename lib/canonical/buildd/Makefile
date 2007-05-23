all: clean deb


deb:
	dpkg-buildpackage -rfakeroot -b

clean:
	fakeroot debian/rules clean
	rm -f launchpad-buildd*deb
	rm -f ../launchpad-buildd*changes
