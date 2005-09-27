# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""BugCve linker interfaces."""

__metaclass__ = type

__all__ = ['IBugCve']

from zope.interface import Interface
from zope.schema import Int
from zope.i18nmessageid import MessageIDFactory

_ = MessageIDFactory('launchpad')

class IBugCve(Interface):
    """A link between a bug and a CVE entry."""

    bug = Int(title=_('Bug Number'), required=True, readonly=True,
        description=_("Enter the Malone bug number that you believe is "
        "describing the same issue as this CVE."))
    cve = Int(title=_('Cve Sequence'), required=True, readonly=True,
        description=_("Enter the CVE sequence number (XXXX-XXXX) that "
        "describes the same issue as this bug is addressing."))

