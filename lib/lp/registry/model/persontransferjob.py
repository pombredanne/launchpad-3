# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Job classes related to PersonTransferJob are in here."""

__metaclass__ = type
__all__ = [
    'AddMemberNotificationJob',
    'PersonTransferJob',
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
from lp.registry.enum import PersonTransferJobType
from lp.registry.interfaces.membershipjob import (
    IPersonTransferJob,
    IPersonTransferJobSource,
    IAddMemberNotificationJob,
    IAddMemberNotificationJobSource,
    )
from lp.registry.model.person import Person
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob


class PersonTransferJob(Storm):
    """Base class for team membership and person merge jobs."""

    implements(IPersonTransferJob)

    __storm_table__ = 'PersonTransferJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    major_person_id = Int(name='major_person')
    major_person = Reference(major_person_id, Person.id)

    minor_person_id = Int(name='minor_person')
    minor_person = Reference(minor_person_id, Person.id)

    job_type = EnumCol(enum=PersonTransferJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, major_person, minor_person, job_type, metadata):
        """Constructor.

        :param major_person: The person or team that is receiving or losing
                             the minor person.
        :param minor_person: The person or team being added to
                             the major_person.
        :param job_type: The specific membership action being performed.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(PersonTransferJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.job_type = job_type
        self.major_person = major_person
        self.minor_person = minor_person
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    @classmethod
    def get(cls, key):
        """Return the instance of this class whose key is supplied."""
        store = IMasterStore(PersonTransferJob)
        instance = store.get(cls, key)
        if instance is None:
            raise SQLObjectNotFound(
                'No occurrence of %s has key %s' % (cls.__name__, key))
        return instance


class PersonTransferJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from PersonTransferJob."""
    delegates(IPersonTransferJob)
    classProvides(IPersonTransferJobSource)

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        return (
            '<%(job_type)s branch job (%(id)s) for %(minor_person)s '
            'as part of %(major_person)s>' % {
                'job_type': self.context.job_type.name,
                'id': self.context.id,
                'minor_person': self.minor_person.name,
                'major_person': self.major_person.name,
                })

    @classmethod
    def create(cls, major_person, minor_person, metadata):
        """See `IPersonTransferJob`."""
        # If there's already a job for the membership, don't create a new one.
        job = IStore(PersonTransferJob).find(
            PersonTransferJob,
            And(PersonTransferJob.major_person == major_person,
                PersonTransferJob.minor_person == minor_person))
        job = PersonTransferJob(
            major_person, minor_person, cls.class_job_type, {})
        return cls(job)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready PersonTransferJobs."""
        store = IMasterStore(PersonTransferJob)
        jobs = store.find(
            PersonTransferJob,
            And(PersonTransferJob.job_type == cls.class_job_type,
                PersonTransferJob.job.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('major_person_name', self.context.major_person.name),
            ('minor_person_name', self.context.minor_person.name),
            ])
        return vars


class AddMemberNotificationJob(PersonTransferJobDerived):
    """A Job that sends email notifications about adding a team member."""

    implements(IAddMemberNotificationJob)
    classProvides(IAddMemberNotificationJobSource)

    class_job_type = PersonTransferJobType.ADD_MEMBER_NOTIFICATION
