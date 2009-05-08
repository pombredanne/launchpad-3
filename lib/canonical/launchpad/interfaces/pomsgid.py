# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from canonical.launchpad import _

from zope.interface import Interface
from zope.schema import Int, Text

__metaclass__ = type

__all__ = ('IPOMsgID', )

class IPOMsgID(Interface):
    """A PO message ID."""

    id = Int(
        title=_("The identifier of this POMsgID."),
        readonly=True, required=True)

    msgid = Text(
        title=_(u"A msgid string."))
