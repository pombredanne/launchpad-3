# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Processor and ProcessorFamily features."""

from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.soyuz.interfaces.processor import (
    IProcessor,
    IProcessorFamily,
    IProcessorFamilySet,
    )
from lp.testing import TestCaseWithFactory


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
        proc = family.addProcessor("avr2001", "The 2001 AVR", "Fast as light.")
        self.assertProvides(proc, IProcessor)
        self.assertEquals(family, proc.family)

    def test_get_restricted(self):
        """Test retrieving all restricted processors."""
        family_set = getUtility(IProcessorFamilySet)
        normal_family = getUtility(IProcessorFamilySet).new("avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        restricted_family = getUtility(IProcessorFamilySet).new("5051", "5051",
            "Another small processor family", restricted=True)
        self.assertFalse(normal_family in family_set.getRestricted())
        self.assertTrue(restricted_family in family_set.getRestricted())
