LOCALEDIR='launchpad/locale'
I18NDOMAIN='launchpad'

all: launchpad.pot

launchpad.pot:
	../sourcecode/zope/utilities/i18nextract.py -p canonical -o $(LOCALEDIR) -d $(I18NDOMAIN)
