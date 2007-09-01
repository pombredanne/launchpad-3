# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('IPOMsgIDSighting', )

class IPOMsgIDSighting(Interface):
    """A message ID from a template."""

    potmsgset = Attribute("The message set for this sighting.")

    pomsgid_ = Attribute("The msgid that is beeing sighted.")

    datefirstseen = Attribute("First time we saw the msgid.")

    datelastseen = Attribute("Last time we saw the msgid.")

    inlastrevision = Attribute("""True if this sighting is currently in last
        imported template or POFile, otherwise false.""")

    pluralform = Attribute("0 if it's singular and 1 if it's plural")
