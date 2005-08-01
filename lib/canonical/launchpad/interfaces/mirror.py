# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Mirror interfaces."""

__metaclass__ = type

__all__ = [
    'IMirror',
    ]

from zope.schema import Bool, Datetime, Int, TextLine
from canonical.launchpad.fields import Description
from zope.interface import Interface
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IMirror(Interface):
    """A Mirror Object"""

    owner = Int(title=_("Owner"), required=True,
                description=_("The Mirror Owner."))
    baseurl = TextLine(title=_("Base URL"), required=True,
                       description=_("The mirror url base."))

    country = Int(title=_("Country"), required=True,
                  description=_("Country where the mirror is located."))
    name = TextLine(title=_("Name"), required=True,
                    description=_("Mirror valid name."))

    description = Description(title=_("Description"), required=True,
        description=_("A detailed description of this mirror."))

    freshness = Int(title=_("Freshness"), required=True)
    lastcheckeddate = Datetime(title=_("LastCheckedDate"))
    approved = Bool(title=_('Approved'), required=True)

