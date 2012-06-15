# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Job classes related to the sharing feature are in here."""

__metaclass__ = type


__all__ = [
    'RemoveBugSubscriptionsJob',
    ]

import contextlib
import logging

from lazr.delegates import delegates
from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
import simplejson
from sqlobject import SQLObjectNotFound
from storm.expr import (
    And,
    In,
    Join,
    Not,
    Or,
    Select,
    )
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from storm.store import Store
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bugtaskflat import BugTaskFlat
from lp.bugs.model.bugtasksearch import (
    get_bug_privacy_filter_terms,
    )
from lp.registry.enums import InformationType
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.sharingjob import (
    IRemoveBugSubscriptionsJob,
    IRemoveBugSubscriptionsJobSource,
    ISharingJob,
    ISharingJobSource,
    )
from lp.registry.model.distribution import Distribution
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.registry.model.teammembership import TeamParticipation
from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.lpstorm import IStore
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import BaseRunnableJob
from lp.services.mail.sendmail import format_address_for_person
from lp.services.webapp import errorlog


class SharingJobType(DBEnumeratedType):
    """Values that ISharingJob.job_type can take."""

    REMOVE_GRANTEE_SUBSCRIPTIONS = DBItem(0, """
        Remove subscriptions of artifacts which are inaccessible.

        This job removes subscriptions to artifacts when access is
        no longer possible because a user no longer has an access
        grant (either direct or indirect via team membership).
        """)

    REMOVE_BUG_SUBSCRIPTIONS = DBItem(1, """
        Remove subscriptions for users who can no longer access bugs.

        This job removes subscriptions to a bug when access is
        no longer possible because the subscriber no longer has an access
        grant (either direct or indirect via team membership).
        """)


class SharingJob(StormBase):
    """Base class for jobs related to branch merge proposals."""

    implements(ISharingJob)

    __storm_table__ = 'SharingJob'

    id = Int(primary=True)

    job_id = Int('job')
    job = Reference(job_id, Job.id)

    product_id = Int(name='product')
    product = Reference(product_id, Product.id)

    distro_id = Int(name='distro')
    distro = Reference(distro_id, Distribution.id)

    grantee_id = Int(name='grantee')
    grantee = Reference(grantee_id, Person.id)

    job_type = EnumCol(enum=SharingJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, job_type, pillar, grantee, metadata):
        """Constructor.

        :param job_type: The BranchMergeProposalJobType of this job.
        :param metadata: The type-specific variables, as a JSON-compatible
            dict.
        """
        super(SharingJob, self).__init__()
        json_data = simplejson.dumps(metadata)
        self.job = Job()
        self.job_type = job_type
        self.grantee = grantee
        self.product = self.distro = None
        if IProduct.providedBy(pillar):
            self.product = pillar
        else:
            self.distro = pillar
        # XXX AaronBentley 2009-01-29 bug=322819: This should be a bytestring,
        # but the DB representation is unicode.
        self._json_data = json_data.decode('utf-8')

    def destroySelf(self):
        Store.of(self).remove(self)

    def makeDerived(self):
        return SharingJobDerived.makeSubclass(self)


class SharingJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from SharingJob."""

    __metaclass__ = EnumeratedSubclass

    delegates(ISharingJob)
    classProvides(ISharingJobSource)

    @staticmethod
    @contextlib.contextmanager
    def contextManager():
        """See `IJobSource`."""
        errorlog.globalErrorUtility.configure('ISharingJobSource')
        yield

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        if self.grantee:
            return '<%(job_type)s job for %(grantee)s and %(pillar)s>' % {
                'job_type': self.context.job_type.name,
                'grantee': self.grantee.displayname,
                'pillar': self.pillar_text,
                }
        else:
            return '<%(job_type)s job>' % {
                'job_type': self.context.job_type.name,
            }

    @property
    def pillar(self):
        if self.product:
            return self.product
        else:
            return self.distro

    @property
    def pillar_text(self):
        return self.pillar.displayname if self.pillar else 'all pillars'

    @property
    def log_name(self):
        return self.__class__.__name__

    @classmethod
    def create(cls, pillar, grantee, metadata):
        base_job = SharingJob(cls.class_job_type, pillar, grantee, metadata)
        job = cls(base_job)
        job.celeryRunOnCommit()
        return job

    @classmethod
    def get(cls, job_id):
        """Get a job by id.

        :return: the SharingJob with the specified id, as the
            current SharingJobDereived subclass.
        :raises: SQLObjectNotFound if there is no job with the specified id,
            or its job_type does not match the desired subclass.
        """
        job = SharingJob.get(job_id)
        if job.job_type != cls.class_job_type:
            raise SQLObjectNotFound(
                'No object found with id %d and type %s' % (job_id,
                cls.class_job_type.title))
        return cls(job)

    @classmethod
    def iterReady(cls):
        """See `IJobSource`.

        This version will emit any ready job based on SharingJob.
        """
        store = IStore(SharingJob)
        jobs = store.find(
            SharingJob,
            And(SharingJob.job_type == cls.class_job_type,
                SharingJob.job_id.is_in(Job.ready_jobs)))
        return (cls.makeSubclass(job) for job in jobs)

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('sharing_job_id', self.context.id),
            ('sharing_job_type', self.context.job_type.title)])
        if self.grantee:
            vars.append(('grantee', self.grantee.name))
        if self.product:
            vars.append(('product', self.product.name))
        if self.distro:
            vars.append(('distro', self.distro.name))
        return vars


class RemoveBugSubscriptionsJob(SharingJobDerived):
    """See `IRemoveBugSubscriptionsJob`."""

    implements(IRemoveBugSubscriptionsJob)
    classProvides(IRemoveBugSubscriptionsJobSource)
    class_job_type = SharingJobType.REMOVE_BUG_SUBSCRIPTIONS

    config = config.IRemoveBugSubscriptionsJobSource

    @classmethod
    def create(cls, requestor, bugs=None, grantee=None, pillar=None,
               information_types=None):
        """See `IRemoveBugSubscriptionsJob`."""

        bug_ids = [bug.id for bug in bugs or []]
        information_types = [
            info_type.value for info_type in information_types or []
        ]
        metadata = {
            'bug_ids': bug_ids,
            'information_types': information_types,
            'requestor.id': requestor.id
        }
        return super(RemoveBugSubscriptionsJob, cls).create(
            pillar, grantee, metadata)

    @property
    def requestor_id(self):
        return self.metadata['requestor.id']

    @property
    def requestor(self):
        return getUtility(IPersonSet).get(self.requestor_id)

    @property
    def bug_ids(self):
        return self.metadata['bug_ids']

    @property
    def bugs(self):
        return getUtility(IBugSet).getByNumbers(self.bug_ids)

    @property
    def information_types(self):
        return [
            InformationType.items[value]
            for value in self.metadata['information_types']]

    def getErrorRecipients(self):
        # If something goes wrong we want to let the requestor know as well
        # as the pillar maintainer (if there is a pillar).
        result = set()
        result.add(format_address_for_person(self.requestor))
        for bug in self.bugs:
            for pillar in bug.affected_pillars:
                if pillar.owner.preferredemail:
                    result.add(format_address_for_person(pillar.owner))
        return list(result)

    def getOperationDescription(self):
        return 'removing subscriptions for bugs %s' % self.bug_ids

    def run(self):
        """See `IRemoveBugSubscriptionsJob`."""

        logger = logging.getLogger()
        logger.info(self.getOperationDescription())

        # Find all bug subscriptions for which the subscriber cannot see the
        # bug.
        invisible_filter = (
            Not(Or(*get_bug_privacy_filter_terms(BugSubscription.person_id))))
        filters = [invisible_filter]

        if self.bug_ids:
            filters.append(BugTaskFlat.bug_id.is_in(self.bug_ids))
        else:
            if self.information_types:
                filters.append(
                    BugTaskFlat.information_type.is_in(self.information_types))
            if self.product:
                filters.append(
                    BugTaskFlat.product == self.product)
            if self.distro:
                filters.append(
                    BugTaskFlat.distribution == self.distro)

        if self.grantee:
            filters.append(
                In(BugSubscription.person_id,
                    Select(
                        TeamParticipation.personID,
                        where=TeamParticipation.team == self.grantee)))
        subscriptions = IStore(BugSubscription).using(
            BugSubscription,
            Join(BugTaskFlat, BugTaskFlat.bug_id == BugSubscription.bug_id)
            ).find(BugSubscription, *filters).config(distinct=True)
        for sub in subscriptions:
            sub.bug.unsubscribe(
                sub.person, self.requestor, ignore_permissions=True)
