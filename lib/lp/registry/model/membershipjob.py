# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to MembershipJob are in here."""

__metaclass__ = type
__all__ = [
    'AddMemberNotificationJob',
    'MembershipJob',
    ]

from lazr.delegates import delegates
import simplejson
from sqlobject import SQLObjectNotFound
from storm.base import Storm
from storm.expr import And
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.interface import (
    classProvides,
    implements,
    )


from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.registry.enum import MembershipJobType
from lp.registry.interfaces.membershipjob import (
    IMembershipJob,
    IMembershipJobSource,
    IAddMemberNotificationJob,
    IAddMemberNotificationJobSource,
    )
from lp.registry.model.person import Person
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob


class MembershipJob(Storm):
    """Base class for jobs making team membership changes."""

    implements(IMembershipJob)

    __storm_table__ = 'MembershipJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    super_team_id = Int(name='super_team')
    super_team = Reference(super_team_id, Person.id)

    new_member_id = Int(name='new_member')
    new_member = Reference(new_member_id, Person.id)

    job_type = EnumCol(enum=MembershipJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, super_team, new_member, job_type, metadata):
        """Constructor.

        :param super_team: The team that is getting a new member.
        :param new_member: The person or team being added to the super_team.
        :param job_type: The specific membership action being performed.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(MembershipJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.job_type = job_type
        self.super_team = super_team
        self.new_member = new_member
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    @classmethod
    def get(cls, key):
        """Return the instance of this class whose key is supplied."""
        store = IMasterStore(MembershipJob)
        instance = store.get(cls, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurrence of %s has key %s' % (cls.__name__, key))
        return instance


class MembershipJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from MembershipJob."""
    delegates(IMembershipJob)
    classProvides(IMembershipJobSource)

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        return (
            '<%(job_type)s branch job (%(id)s) for %(new_member)s '
            'as member of %(super_team)s>' % {
                'job_type': self.context.job_type.name,
                'id': self.context.id,
                'new_member': self.new_member.name,
                'super_team': self.new_member.name,
                })

    @classmethod
    def create(cls, super_team, new_member, metadata):
        """See `IMembershipJob`."""
        # If there's already a job for the membership, don't create a new one.
        job = IStore(MembershipJob).find(
            MembershipJob,
            And(MembershipJob.super_team == super_team,
                MembershipJob.new_member == new_member))
        job = MembershipJob(super_team, new_member, cls.class_job_type, {})
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready MembershipJobs."""
        store = IMasterStore(MembershipJob)
        jobs = store.find(
            MembershipJob,
            And(MembershipJob.job_type == cls.class_job_type,
                MembershipJob.job.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('super_team_name', self.context.super_team.name),
            ('new_member_name', self.context.new_member.name),
            ])
        return vars


class AddMemberNotificationJob(MembershipJobDerived):
    """A Job that sends email notifications about adding a team member."""

    implements(IAddMemberNotificationJob)
    classProvides(IAddMemberNotificationJobSource)

    class_job_type = MembershipJobType.ADD_MEMBER_NOTIFICATION
