# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['BuildfarmJob']


from zope.interface import implements

from lp.buildmaster.interfaces.buildfarmjob import IBuildfarmJob


class BuildfarmJob:
    """Mix-in class for `IBuildfarmJob` implementations."""
    implements(IBuildfarmJob)

    def score(self):
        """See `IBuildfarmJob`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `IBuildfarmJob`."""
        raise NotImplementedError

    def getName(self):
        """See `IBuildfarmJob`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `IBuildfarmJob`."""
        pass

    def jobReset(self):
        """See `IBuildfarmJob`."""
        pass

    def jobAborted(self):
        """See `IBuildfarmJob`."""
        pass

