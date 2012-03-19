# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ProductJobs."""

__metaclass__ = type

from zope.interface import (
    classProvides,
    implements,
    )

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
        product = self.factory.makeProduct('fnord')
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
