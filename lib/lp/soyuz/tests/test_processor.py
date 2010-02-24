# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Processor and ProcessorFamily features."""

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.processor import (IProcessor, IProcessorFamily,
    IProcessorFamilySet)
from lp.testing import TestCaseWithFactory


class ProcessorFamilyTests(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_create(self):
        family = getUtility(IProcessorFamilySet).new("avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        self.assertProvides(family, IProcessorFamily)

    def test_add_processor(self):
        family = getUtility(IProcessorFamilySet).new("avr", "Atmel AVR",
            "The Modified Harvard architecture 8-bit RISC processors.")
        proc = family.addProcessor("avr2001", "The 2001 AVR", "Fast as light.")
        self.assertProvides(proc, IProcessor)
