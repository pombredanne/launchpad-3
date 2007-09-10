# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Helper module reused in different tests."""

__metaclass__ = type

__all__ = [
    'is_valid_mofile',
    ]

def is_valid_mofile(mofile):
    """Test whether a string is a valid MO file."""
    # There are different magics for big- and little-endianness, so we
    # test for both.
    be_magic = '\x95\x04\x12\xde'
    le_magic = '\xde\x12\x04\x95'

    return mofile[:len(be_magic)] in (be_magic, le_magic)
