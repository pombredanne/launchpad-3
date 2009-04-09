# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interface for the branch scanner."""

__metaclass__ = type
__all__ = [
    'IBranchScanner',
    ]


from zope.interface import Interface


class IBranchScanner(Interface):

    def getBranchesToScan():
        """Return an iterator for the branches that need to be scanned."""
