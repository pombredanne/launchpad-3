# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for the Jobs system to update products and send notifications."""

__metaclass__ = type
__all__ = [
    'IProductJob',
    'IProductJobSource',
    'IProductNotificationJob',
    'IProductNotificationJobSource',
    ]

from zope.interface import Attribute
from zope.schema import (
    Int,
    Object,
    )

from lp import _
from lp.registry.interfaces.product import IProduct

from lp.services.job.interfaces.job import (
    IJob,
    IJobSource,
    IRunnableJob,
    )


class IProductJob(IRunnableJob):
    """A Job related to an `IProduct`."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number of this job."))

    job = Object(
        title=_('The common Job attributes'),
        schema=IJob,
        required=True)

    product = Object(
        title=_('The product the job is for'),
        schema=IProduct,
        required=True)

    metadata = Attribute('A dict of data for the job')


class IProductJobSource(IJobSource):
    """An interface for creating and finding `IProductJob`s."""

    def create(product, metadata):
        """Create a new `IProductJob`.

        :param product: An IProduct.
        :param metadata: a dict of configuration data for the job.
            The data must be JSON compatible keys and values.
        """

    def find(product=None, date_since=None, job_type=None):
        """Find `IProductJob`s that match the specified criteria.

        :param product: Match jobs for specific product.
        :param date_since: Match jobs since the specified date.
        :param job_type: Match jobs of a specific type. Type is expected
            to be a class name.
        :return: A `ResultSet` yielding `IProductJob`.
        """


class IProductNotificationJob(IProductJob):
    """A job then sends a notification about a product."""


class IProductNotificationJobSource(IProductJobSource):
    """An interface for creating and finding `IProductNotificationJob`s."""
