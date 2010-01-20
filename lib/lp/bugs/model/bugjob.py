# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to BugJobs are in here."""

__metaclass__ = type
__all__ = [
    'BugJob',
    ]

import simplejson

from storm.base import Storm
from storm.locals import Int, Reference, Unicode
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements

from canonical.database.enumcol import EnumCol
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE)

from lp.bugs.interfaces.bugjob import BugJobType, IBugJob
from lp.bugs.model.bug import Bug
from lp.services.job.model.job import Job


class BugJob(Storm):
    """Base class for jobs related to Bugs."""

    implements(IBugJob)

    __storm_table__ = 'BugJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    bug_id = Int(name='bug')
    bug = Reference(bug_id, Bug.id)

    job_type = EnumCol(enum=BugJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, bug, job_type, metadata):
        """Constructor.

        :param bug: The proposal this job relates to.
        :param job_type: The BugJobType of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        Storm.__init__(self)
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.bug = bug
        self.job_type = job_type
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    def sync(self):
        store = Store.of(self)
        store.flush()
        store.autoreload(self)

    def destroySelf(self):
        Store.of(self).remove(self)

    @classmethod
    def selectBy(klass, **kwargs):
        """Return selected instances of this class.

        At least one pair of keyword arguments must be supplied.
        foo=bar is interpreted as 'select all instances of
        BugJob whose property "foo" is equal to "bar"'.
        """
        assert len(kwargs) > 0
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(klass, **kwargs)

    @classmethod
    def get(klass, key):
        """Return the instance of this class whose key is supplied."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.get(klass, key)
