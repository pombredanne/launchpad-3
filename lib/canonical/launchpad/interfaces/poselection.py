# Copyright 2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Field, Datetime, Object
from canonical.launchpad.interfaces import IPerson

__metaclass__ = type
__all__ = ('IPOSelection', )

class IPOSelection(Interface):
    """The selection of a translation in a PO file (published) or in Rosetta
    (active)."""

    pomsgset = Attribute("The PO message set for which is this sighting.")
    pluralform = Attribute("The # of pluralform that we are sighting.")

    activesubmission = Field(
        title=u'The submission that made this active.',
        required=False)
    publishedsubmission = Field(u'The submission where this was '
        u'published in the public pofile for the first time.',
        required=False)
    reviewer = Object(
        title=u'The person who did the review and accepted current active'
              u'translation.',
        required=False, schema=IPerson)
    date_reviewed = Datetime(
        title=u'The date when this message was reviewed for last time.',
        required=False)

    def isNewerThan(timestamp):
        """Whether the selection is active and newer than the given timestamp.

        :arg timestamp: A DateTime object with a timestamp.

        """
