# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['SoyuzJob']


from zope.interface import implements

from lp.soyuz.interfaces.soyuzjob import ISoyuzJob


class SoyuzJob:
    """Mix-in class for `ISoyuzJob` implementations."""
    implements(ISoyuzJob)

    def score(self):
        """See `ISoyuzJob`."""
        raise NotImplementedError

    def getLogFileName(self):
        """See `ISoyuzJob`."""
        raise NotImplementedError

    def getName(self):
        """See `ISoyuzJob`."""
        raise NotImplementedError

    def jobStarted(self):
        """See `ISoyuzJob`."""
        pass

    def jobReset(self):
        """See `ISoyuzJob`."""
        pass

    def jobAborted(self):
        """See `ISoyuzJob`."""
        pass

