# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

__metaclass__ = type
__all__ = [
    'IBranchRef',
    ]

from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _

class IBranchRef(Interface):
    """A branch reference '.bzr' directory.

    This interface is for use in the browser code to implement these
    directories.
    """

    branch = Choice(
        title=_('Series Branch'),
        vocabulary='Branch',
        readonly=True,
        description=_("The Bazaar branch for this series."))
