# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Job classes related to the sharing feature are in here."""

__metaclass__ = type


__all__ = [
    'RemoveSubscriptionsJob',
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
from storm.expr import And
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
from zope.security.proxy import removeSecurityProxy

from lp.bugs.interfaces.bug import IBugSet
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.sharingjob import (
    IRemoveSubscriptionsJob,
    IRemoveSubscriptionsJobSource,
    ISharingJob,
    ISharingJobSource,
    )
from lp.registry.model.distribution import Distribution
from lp.registry.model.person import Person
from lp.registry.model.product import Product
from lp.services.config import config
from lp.services.database.enumcol import EnumCol
from lp.services.database.lpstorm import IStore
from lp.services.database.stormbase import StormBase
from lp.services.job.model.job import (
    EnumeratedSubclass,
    Job,
    )
from lp.services.job.runner import (
    BaseRunnableJob,
    )
from lp.services.mail.sendmail import format_address_for_person
from lp.services.webapp import errorlog


class SharingJobType(DBEnumeratedType):
    """Values that ISharingJob.job_type can take."""

    REMOVE_SUBSCRIPTIONS = DBItem(0, """
        Remove subscriptions when access is revoked.

        This job removes subscriptions to artifacts when access is
        revoked for a particular information type or artifact.
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
        errorlog.globalErrorUtility.configure('sharing_jobs')
        yield

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        return '<%(job_type)s job for %(grantee)s and %(pillar)s>' % {
            'job_type': self.context.job_type.name,
            'grantee': self.grantee.displayname,
            'pillar': self.pillar.displayname,
            }

    @property
    def pillar(self):
        if self.product:
            return self.product
        else:
            return self.distro

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
            ('sharing_job_type', self.context.job_type.title),
            ('grantee', self.grantee.name)])
        if self.product:
            vars.append(('product', self.product.name))
        if self.distro:
            vars.append(('distro', self.distro.name))
        return vars


class RemoveSubscriptionsJob(SharingJobDerived):
    """See `IRemoveSubscriptionsJob`."""

    implements(IRemoveSubscriptionsJob)
    classProvides(IRemoveSubscriptionsJobSource)
    class_job_type = SharingJobType.REMOVE_SUBSCRIPTIONS

    config = config.sharing_jobs

    @classmethod
    def create(cls, pillar, grantee, requestor, bugs=None, branches=None):
        """See `IRemoveSubscriptionsJob`."""

        bug_ids = [
            bug.id for bug in bugs or []
        ]
        branch_names = [
            branch.unique_name for branch in branches or []
        ]
        metadata = {
            'bug_ids': bug_ids,
            'branch_names': branch_names,
            'requestor.id': requestor.id
        }
        return super(RemoveSubscriptionsJob, cls).create(
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
    def branch_names(self):
        return self.metadata['branch_names']

    def getErrorRecipients(self):
        # If something goes wrong we want to let the requestor know as well
        # as the pillar maintainer.
        result = [format_address_for_person(self.requestor)]
        if self.pillar.owner.preferredemail:
            result.append(format_address_for_person(self.pillar.owner))
        return result

    def getOperationDescription(self):
        return ('removing subscriptions for artifacts '
            'for %s on %s' %
            (self.grantee.displayname,
             self.pillar.displayname))

    def run(self):
        """See `IRemoveSubscriptionsJob`."""

        logger = logging.getLogger()
        logger.info(self.getOperationDescription())

        # Unsubscribe grantee from the specified bugs.
        if self.bug_ids:
            bugs = getUtility(IBugSet).getByNumbers(self.bug_ids)
            for bug in bugs:
                removeSecurityProxy(bug).unsubscribe(
                    self.grantee, self.requestor)

        # Unsubscribe grantee from the specified branches.
        if self.branch_names:
            branches = [
                getUtility(IBranchLookup).getByUniqueName(branch_name)
                for branch_name in self.branch_names]
            for branch in branches:
                branch.unsubscribe(self.grantee, self.requestor)
