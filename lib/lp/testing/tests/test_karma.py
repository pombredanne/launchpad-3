# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX: Module docstring goes here."""

__metaclass__ = type

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class TestKarmaRecorder(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_record(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()

        recorder = self.installKarmaRecorder()
        person.assignKarma('bugcreated', product=product)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual(person, karma.person)
        self.assertEqual(product, karma.product)

    def test_record_person(self):
        person = self.factory.makePerson()
        unrelated_person = self.factory.makePerson()
        product = self.factory.makeProduct()

        recorder = self.installKarmaRecorder(person=person)
        person.assignKarma('bugfixed', product=product)
        unrelated_person.assignKarma('bugfixed', product=product)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual(person, karma.person)

    def test_record_action_name(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()

        recorder = self.installKarmaRecorder(action_name='bugrejected')
        person.assignKarma('bugrejected', product=product)
        person.assignKarma('bugaccepted', product=product)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual('bugrejected', karma.action.name)

    def test_record_product(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        other_product = self.factory.makeProduct()
        package = self.factory.makeDistributionSourcePackage()

        recorder = self.installKarmaRecorder(product=product)
        person.assignKarma('faqcreated', product=other_product)
        person.assignKarma('faqcreated', product=product)
        person.assignKarma(
            'faqcreated', sourcepackagename=package.sourcepackagename,
            distribution=package.distribution)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual(product, karma.product)

    def test_record_distribution(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        package = self.factory.makeDistributionSourcePackage()
        distro = package.distribution
        other_distro = self.factory.makeDistribution()

        recorder = self.installKarmaRecorder(distribution=distro)
        person.assignKarma(
            'faqcreated', distribution=distro,
            sourcepackagename=package.sourcepackagename)
        person.assignKarma(
            'faqcreated', distribution=other_distro,
            sourcepackagename=package.sourcepackagename)
        person.assignKarma('faqcreated', product=product)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual(distro, karma.distribution)

    def test_record_sourcepackagename(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        package = self.factory.makeDistributionSourcePackage()
        packagename = package.sourcepackagename
        other_packagename = self.factory.makeSourcePackageName()

        recorder = self.installKarmaRecorder(sourcepackagename=packagename)
        person.assignKarma(
            'faqcreated', distribution=package.distribution,
            sourcepackagename=packagename)
        person.assignKarma(
            'faqcreated', distribution=package.distribution,
            sourcepackagename=other_packagename)
        person.assignKarma('faqcreated', product=product)

        self.assertEqual(1, len(recorder.karma_events))
        karma = recorder.karma_events[0]
        self.assertEqual(packagename, karma.sourcepackagename)

    def test_record_can_be_replaced(self):
        person = self.factory.makePerson()
        product = self.factory.makeProduct()

        recorder = self.installKarmaRecorder()
        recorder.record = FakeMethod()

        person.assignKarma('faqedited', product=product)
        self.assertEqual(1, recorder.record.call_count)
        call_args, call_kwargs = recorder.record.calls[0]
        self.assertEqual(1, len(call_args))
        self.assertEqual({}, call_kwargs)
        self.assertEqual('faqedited', call_args[0].action.name)
