#!/usr/bin/env python

# arch-tag: d7be3bf8-9f05-401c-9ffc-06f4dd19af48
# Author: David Allouche <david.allouche@canonical.com>
# Copyright (C) 2004 Canonical Software
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Test suite for Canonical arch modules."""

import unittest
import sys


class Imports(unittest.TestCase):

    """Test that modules import without error."""

    tests = []

    def import_zope_interface(self):
        """Import zope.interface (dependence)."""
        import zope.interface
    tests.append('import_zope_interface')

    def import_canonical_arch_interfaces(self):
        """Import canonical.launchpad.interfaces."""
        import canonical.launchpad.interfaces
    tests.append('import_canonical_arch_interfaces')

def test_suite():
    return unittest.TestSuite()

def main(argv):
    """Run the full test suite."""
    suite = unittest.TestSuite()
    def addTests(klass): suite.addTests(map(klass, klass.tests))
    addTests(Imports)
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful(): return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
