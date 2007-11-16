# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""BugCve linker interfaces."""

__metaclass__ = type

__all__ = ['IBugCve']

from zope.schema import Object
from canonical.launchpad import _
from canonical.launchpad.interfaces.buglink import IBugLink
from canonical.launchpad.interfaces.cve import ICve

class IBugCve(IBugLink):
    """A link between a bug and a CVE entry."""

    cve = Object(title=_('Cve Sequence'), required=True, readonly=True,
        description=_("Enter the CVE sequence number (XXXX-XXXX) that "
        "describes the same issue as this bug is addressing."),
        schema=ICve)

