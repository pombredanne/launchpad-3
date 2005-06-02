# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOTranslationSighting', )

class IPOTranslationSighting(Interface):
    """A sighting of a translation in a PO file."""

    pomsgset = Attribute("The PO Message Set of the translation.")

    potranslation = Attribute("The translation that was provided.")

    license = Attribute("The license under which the translation was provided.")

    datefirstseen = Attribute("The first time we saw this translation.")

    datelastactive = Attribute("The last time this translation was active.")

    inlastrevision = Attribute("""True if this sighting is currently in last
        imported POFile, otherwise false.""")

    pluralform = Attribute("The # of pluralform that we are sighting.")

    active = Attribute("If this is the latest translation we should use.")

    origin = Attribute("Where the sighting originally came from.")

    person = Attribute("The owner of this sighting.")

