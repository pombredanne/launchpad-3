# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type


from unittest import TestCase, TestLoader


class LoggingSupportTests(TestCase):

    pass


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

