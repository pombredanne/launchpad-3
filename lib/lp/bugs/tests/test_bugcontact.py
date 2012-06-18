# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running tests against IHasBugcontact
implementations.
"""

import unittest

from lp.bugs.tests.test_structuralsubscriptiontarget import (
    distributionSetUp,
    productSetUp,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    tearDown,
    )


def test_suite():
    """Return the `IHasBugSupervisor` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        distributionSetUp,
        ]

    testname = 'has-bug-supervisor.txt'
    for setUpMethod in setUpMethods:
        id_ext = "%s-%s" % (testname, setUpMethod.func_name)
        test = LayeredDocFileSuite(
            testname,
            id_extensions=[id_ext],
            setUp=setUpMethod, tearDown=tearDown,
            layer=DatabaseFunctionalLayer)
        suite.addTest(test)

    return suite
