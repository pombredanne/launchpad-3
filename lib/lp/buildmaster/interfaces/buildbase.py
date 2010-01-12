# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build interfaces."""

__metaclass__ = type

__all__ = ['IBuildBase']

from zope.interface import Interface

class IBuildBase(Interface):
    def handleStatus(status, queueItem, librarian, buildid, filemap,
                     dependencies):
        """Handle a finished build status from a slave.

        The status should be a slave build status string with the
        'BuildStatus.' stripped such as 'OK

        Different actions will be taken depending on the given status.
        """

    def getLogFromSlave(queueItem):
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """
