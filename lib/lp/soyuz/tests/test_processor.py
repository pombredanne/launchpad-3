# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Processor and ProcessorFamily features."""

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )

from lp.soyuz.interfaces.processor import (
    IProcessor,
    IProcessorFamily,
    IProcessorFamilySet,
    IProcessorSet,
    ProcessorNotFound,
    )
from lp.testing import (
    ExpectedException,
    logout,
    TestCaseWithFactory,
    )


class ProcessorFamilyTests(TestCaseWithFactory):
    """Test ProcessorFamily."""

    layer = LaunchpadZopelessLayer

    def test_create(self):
        """Test adding a new ProcessorFamily."""
        family = getUtility(IProcessorFamilySet).new("avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        self.assertProvides(family, IProcessorFamily)

    def test_add_processor(self):
        """Test adding a new Processor to a ProcessorFamily."""
        family = getUtility(IProcessorFamilySet).new("avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        proc = family.addProcessor(
            "avr2001", "The 2001 AVR", "Fast as light.")
        self.assertProvides(proc, IProcessor)
        self.assertEquals(family, proc.family)

    def test_get_restricted(self):
        """Test retrieving all restricted processors."""
        family_set = getUtility(IProcessorFamilySet)
        normal_family = getUtility(IProcessorFamilySet).new(
            "avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        restricted_family = getUtility(IProcessorFamilySet).new(
            "5051", "5051", "Another small processor family",
            restricted=True)
        self.assertFalse(normal_family in family_set.getRestricted())
        self.assertTrue(restricted_family in family_set.getRestricted())


class ProcessorSetTests(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_getByName(self):
        processor_set = getUtility(IProcessorSet)
        q1 = self.factory.makeProcessorFamily(name='q1')
        self.assertEquals(q1.processors[0], processor_set.getByName('q1'))

    def test_getByName_not_found(self):
        processor_set = getUtility(IProcessorSet)
        with ExpectedException(ProcessorNotFound, 'No such processor.*'):
            processor_set.getByName('q1')

    def test_getAll(self):
        processor_set = getUtility(IProcessorSet)
        # Make it easy to filter out sample data
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute("UPDATE Processor SET name = 'sample_data_' || name")
        self.factory.makeProcessorFamily(name='q1')
        self.factory.makeProcessorFamily(name='i686')
        self.factory.makeProcessorFamily(name='g4')
        self.assertEquals(
            ['g4', 'i686', 'q1'],
            sorted(
            processor.name for processor in processor_set.getAll()
            if not processor.name.startswith('sample_data_')))


class ProcessorSetWebServiceTests(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProcessorSetWebServiceTests, self).setUp()
        self.webservice = LaunchpadWebServiceCaller()

    def test_getByName(self):
        self.factory.makeProcessorFamily(name='transmeta')
        logout()

        processor = self.webservice.named_get(
            '/+processors', 'getByName', name='transmeta',
            api_version='devel',
            ).jsonBody()
        self.assertEquals('transmeta', processor['name'])

    def test_default_collection(self):
        # Make it easy to filter out sample data
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        store.execute("UPDATE Processor SET name = 'sample_data_' || name")
        self.factory.makeProcessorFamily(name='q1')
        self.factory.makeProcessorFamily(name='i686')
        self.factory.makeProcessorFamily(name='g4')

        logout()

        collection = self.webservice.get(
            '/+processors?ws.size=10', api_version='devel').jsonBody()
        self.assertEquals(
            ['g4', 'i686', 'q1'],
            sorted(
            processor['name'] for processor in collection['entries']
            if not processor['name'].startswith('sample_data_')))
