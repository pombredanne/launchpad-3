# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Jobs classes to update products and send notifications."""

__metaclass__ = type
__all__ = [
    'ProductJob',
    ]

from lazr.delegates import delegates
import simplejson
from storm.expr import (
    And,
    )
from storm.locals import (
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from lp.registry.enums import ProductJobType
from lp.registry.interfaces.person import (
    IPersonSet,
    )
from lp.registry.interfaces.product import (
    IProduct,
    )
from lp.registry.interfaces.productjob import (
    IProductJob,
    IProductJobSource,
    IProductNotificationJob,
    IProductNotificationJobSource,
    )
from lp.registry.model.product import Product
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.lpstorm import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormbase import StormBase
from lp.services.propertycache import cachedproperty
from lp.services.job.model.job import Job
from lp.services.job.runner import BaseRunnableJob
from lp.services.mail.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from lp.services.mail.mailwrapper import MailWrapper
from lp.services.mail.sendmail import (
    format_address_for_person,
    simple_sendmail,
    )
from lp.services.scripts import log


class ProductJob(StormBase):
    """Base class for product jobs."""

    implements(IProductJob)

    __storm_table__ = 'ProductJob'

    id = Int(primary=True)

    job_id = Int(name='job')
    job = Reference(job_id, Job.id)

    product_id = Int(name='product')
    product = Reference(product_id, Product.id)

    job_type = EnumCol(enum=ProductJobType, notNull=True)

    _json_data = Unicode('json_data')

    @property
    def metadata(self):
        return simplejson.loads(self._json_data)

    def __init__(self, product, job_type, metadata):
        """Constructor.

        :param product: The product the job is for.
        :param job_type: The type job the product needs run.
        :param metadata: A dict of JSON-compatible data to pass to the job.
        """
        super(ProductJob, self).__init__()
        self.job = Job()
        self.product = product
        self.job_type = job_type
        json_data = simplejson.dumps(metadata)
        self._json_data = json_data.decode('utf-8')


class ProductJobDerived(BaseRunnableJob):
    """Intermediate class for deriving from ProductJob.

    Storm classes can't simply be subclassed or you can end up with
    multiple objects referencing the same row in the db. This class uses
    lazr.delegates, which is a little bit simpler than storm's
    infoheritance solution to the problem. Subclasses need to override
    the run() method.
    """

    delegates(IProductJob)
    classProvides(IProductJobSource)

    def __init__(self, job):
        self.context = job

    def __repr__(self):
        return (
            "<{self.__class__.__name__} for {self.product.name} "
            "status={self.job.status}>").format(self=self)

    @classmethod
    def create(cls, product, metadata):
        """See `IProductJob`."""
        if not IProduct.providedBy(product):
            raise TypeError("Product must be an IProduct: %s" % repr(product))
        job = ProductJob(
            product=product, job_type=cls.class_job_type, metadata=metadata)
        return cls(job)

    @classmethod
    def find(cls, product, date_since=None, job_type=None):
        """See `IPersonMergeJobSource`."""
        conditions = [
            ProductJob.job_id == Job.id,
            ProductJob.product == product.id,
            ]
        if date_since is not None:
            conditions.append(
                Job.date_created >= date_since)
        if job_type is not None:
            conditions.append(
                ProductJob.job_type == job_type)
        return DecoratedResultSet(
            IStore(ProductJob).find(
                ProductJob, *conditions), cls)

    @classmethod
    def iterReady(cls):
        """Iterate through all ready ProductJobs."""
        store = IMasterStore(ProductJob)
        jobs = store.find(
            ProductJob,
            And(ProductJob.job_type == cls.class_job_type,
                ProductJob.job_id.is_in(Job.ready_jobs)))
        return (cls(job) for job in jobs)

    @property
    def log_name(self):
        return self.__class__.__name__

    def getOopsVars(self):
        """See `IRunnableJob`."""
        vars = BaseRunnableJob.getOopsVars(self)
        vars.extend([
            ('product', self.context.product.name),
            ])
        return vars


class ProductNotificationJob(ProductJobDerived):
    """A Job that send an email to the product maintainer."""

    implements(IProductNotificationJob)
    classProvides(IProductNotificationJobSource)
    class_job_type = ProductJobType.REVIEWER_NOTIFICATION

    @classmethod
    def create(cls, product, email_template_name, subject, reviewer):
        """See `IProductNotificationJob`."""
        metadata = {
            'email_template_name': email_template_name,
            'subject': subject,
            'reviewer_id': reviewer.id
            }
        return super(ProductNotificationJob, cls).create(product, metadata)

    @property
    def subject(self):
        return self.metadata['subject']

    @property
    def email_template_name(self):
        return self.metadata['email_template_name']

    @cachedproperty
    def reviewer(self):
        return getUtility(IPersonSet).get(self.metadata['reviewer_id'])

    def getErrorRecipients(self):
        """See `IPersonMergeJob`."""
        return [format_address_for_person(self.reviewer)]

    def sendEmailToMaintainer(self, template_name, subject, from_address):
        email_template = get_email_template(
            "%s.txt" % template_name, app='registry')
        if self.product.owner.is_team:
            addresses = self.product.owner.getTeamAdminsEmailAddresses()
        else:
            addresses = get_contact_email_addresses(self.product.owner)
        for address in addresses:
            msg = MailWrapper().format(
                email_template % self.metadata, force_wrap=True)
            simple_sendmail(from_address, address, subject, msg)

    def run(self):
        """Perform the merge."""
        product_name = self.product.name
        template_name = self.email_template_name
        subject = self.subject
        from_address = get_contact_email_addresses(self.reviewer)
        log.debug(
            "%s is sending a %s notification to the %s maintainers",
            self.log_name, template_name, product_name)
        self.sendEmailToMaintainer(template_name, subject, from_address)
        log.debug(
            "%s sent a %s notification to the %s maintainers",
            self.log_name, template_name, product_name)
