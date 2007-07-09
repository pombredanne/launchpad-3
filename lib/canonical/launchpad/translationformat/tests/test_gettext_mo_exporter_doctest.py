# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the gettext_po_parser.txt test.

Tests with different sample .po files so we are sure the parsed data is
correct.
"""

__metaclass__ = type

__all__ = [
    'is_valid_mofile',
    ]

from zope.testing.doctest import DocFileSuite
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags)

def is_valid_mofile(mofile):
     """Test whether a string is a valid MO file."""
     # There are different magics for big- and little-endianness, so we
     # test for both.
     be_magic = '\x95\x04\x12\xde'
     le_magic = ''.join(reversed(be_magic))

     for magic in (be_magic, le_magic):
         if mofile[:len(magic)] == magic:
             return True

     return False

def test_suite():
    return DocFileSuite(
        'gettext_mo_exporter.txt', optionflags=default_optionflags)
