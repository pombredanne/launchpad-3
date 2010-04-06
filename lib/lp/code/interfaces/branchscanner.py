# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for the branch scanner."""

__metaclass__ = type
__all__ = [
    'IBranchScanner',
    ]


from zope.interface import Interface


class IBranchScanner(Interface):

    def getBranchesToScan():
        """Return an iterator for the branches that need to be scanned."""
