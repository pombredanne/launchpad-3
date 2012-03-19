# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ProductJobs."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )

import pytz

from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from lp.registry.enums import ProductJobType
from lp.registry.interfaces.productjob import (
    IProductJob,
    IProductJobSource,
    IProductNotificationJob,
    IProductNotificstionJobSource,
    )
from lp.registry.model.productjob import (
    ProductJob,
    ProductJobDerived,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class ProductJobTestCase(TestCaseWithFactory):
    """Test case for basic ProductJob class."""

    layer = LaunchpadZopelessLayer

    def test_init(self):
        product = self.factory.makeProduct()
        metadata = ('some', 'arbitrary', 'metadata')
        product_job = ProductJob(
            product, ProductJobType.REVIEWER_NOTIFICATION, metadata)
        self.assertEqual(product, product_job.product)
        self.assertEqual(
            ProductJobType.REVIEWER_NOTIFICATION, product_job.job_type)
        expected_json_data = '["some", "arbitrary", "metadata"]'
        self.assertEqual(expected_json_data, product_job._json_data)

    def test_metadata(self):
        # The python structure stored as json is returned as python.
        product = self.factory.makeProduct()
        metadata = {
            'a_list': ('some', 'arbitrary', 'metadata'),
            'a_number': 1,
            'a_string': 'string',
            }
        product_job = ProductJob(
            product, ProductJobType.REVIEWER_NOTIFICATION, metadata)
        metadata['a_list'] = list(metadata['a_list'])
        self.assertEqual(metadata, product_job.metadata)


class FakeProductJob(ProductJobDerived):
    """A class that reuses other interfaces and types for testing."""
    class_job_type = ProductJobType.REVIEWER_NOTIFICATION
    implements(IProductNotificationJob)
    classProvides(IProductNotificstionJobSource)


class OtherFakeProductJob(ProductJobDerived):
    """A class that reuses other interfaces and types for testing."""
    class_job_type = ProductJobType.COMMERCIAL_EXPIRED
    implements(IProductNotificationJob)
    classProvides(IProductNotificstionJobSource)


class ProductJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the ProductJobDerived class."""

    layer = DatabaseFunctionalLayer

    def test_repr(self):
        product = self.factory.makeProduct('fnord')
        metadata = {'foo': 'bar'}
        job = FakeProductJob.create(product, metadata)
        self.assertEqual(
            '<FakeProductJob for fnord status=Waiting>', repr(job))

    def test_create_success(self):
        # Create an instance of ProductJobDerived that delegates to
        # ProductJob.
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        self.assertIs(True, IProductJobSource.providedBy(ProductJobDerived))
        job = FakeProductJob.create(product, metadata)
        self.assertIsInstance(job, ProductJobDerived)
        self.assertIs(True, IProductJob.providedBy(job))
        self.assertIs(True, IProductJob.providedBy(job.context))

    def test_create_raises_error(self):
        # ProductJobDerived.create() raises an error because it
        # needs to be subclassed to work properly.
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        self.assertRaises(
            AttributeError, ProductJobDerived.create, product, metadata)

    def test_iterReady(self):
        # iterReady finds job in the READY status that are of the same type.
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        job_1 = FakeProductJob.create(product, metadata)
        job_2 = FakeProductJob.create(product, metadata)
        job_2.start()
        job_3 = OtherFakeProductJob.create(product, metadata)
        jobs = list(FakeProductJob.iterReady())
        self.assertEqual(1, len(jobs))
        self.assertEqual(job_1, jobs[0])

    def test_find_product(self):
        # Find all the jobs for a product regardless of date or job type.
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        job_1 = FakeProductJob.create(product, metadata)
        job_2 = OtherFakeProductJob.create(product, metadata)
        job_3 = FakeProductJob.create(self.factory.makeProduct(), metadata)
        jobs = list(ProductJobDerived.find(product=product))
        self.assertEqual(2, len(jobs))
        self.assertContentEqual([job_1.id, job_2.id], [job.id for job in jobs])

    def test_find_job_type(self):
        # Find all the jobs for a product and job_type regardless of date.
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        job_1 = FakeProductJob.create(product, metadata)
        job_2 = FakeProductJob.create(product, metadata)
        job_3 = OtherFakeProductJob.create(product, metadata)
        jobs = list(ProductJobDerived.find(
            product, job_type=ProductJobType.REVIEWER_NOTIFICATION))
        self.assertEqual(2, len(jobs))
        self.assertContentEqual([job_1.id, job_2.id], [job.id for job in jobs])

    def test_find_date_since(self):
        # Find all the jobs for a product since a date regardless of job_type.
        now = datetime.now(pytz.utc)
        seven_days_ago = now - timedelta(7)
        thirty_days_ago = now - timedelta(30)
        product = self.factory.makeProduct()
        metadata = {'foo': 'bar'}
        job_1 = FakeProductJob.create(product, metadata)
        removeSecurityProxy(job_1.job).date_created = thirty_days_ago
        job_2 = FakeProductJob.create(product, metadata)
        removeSecurityProxy(job_2.job).date_created = seven_days_ago
        job_3 = OtherFakeProductJob.create(product, metadata)
        removeSecurityProxy(job_3.job).date_created = now
        jobs = list(ProductJobDerived.find(product, date_since=seven_days_ago))
        self.assertEqual(2, len(jobs))
        self.assertContentEqual([job_2.id, job_3.id], [job.id for job in jobs])

    def test_log_name(self):
        # The log_name is the name of the implementing class.
        product = self.factory.makeProduct('fnord')
        metadata = {'foo': 'bar'}
        job = FakeProductJob.create(product, metadata)
        self.assertEqual('FakeProductJob', job.log_name)

    def test_getOopsVars(self):
        # The project name is added to the oops vars.
        product = self.factory.makeProduct('fnord')
        metadata = {'foo': 'bar'}
        job = FakeProductJob.create(product, metadata)
        oops_vars = job.getOopsVars()
        self.assertIs(True, len(oops_vars) > 1)
        self.assertIn(('product', product.name), oops_vars)
