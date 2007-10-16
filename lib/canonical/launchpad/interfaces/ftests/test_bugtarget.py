# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running tests agains IBugTarget implementations."""

__metaclass__ = type

__all__ = []

import random
import unittest

from zope.component import getUtility

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.interfaces import (
    CreateBugParams, IBugTaskSet, IDistributionSet, ILaunchBag, IProductSet,
    IProjectSet)
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def bugtarget_filebug(bugtarget, summary, status=None):
    """File a bug as the current user on the bug target and return it."""
    return bugtarget.createBug(CreateBugParams(
        getUtility(ILaunchBag).user, summary, comment=summary, status=status))


def productSetUp(test):
    """Setup the `IProduct` test."""
    setUp(test)
    test.globs['bugtarget'] = getUtility(IProductSet).getByName('firefox')
    test.globs['filebug'] = bugtarget_filebug


def project_filebug(project, summary, status=None):
    """File a bug on a project.

    Since it's not possible to file a bug on a project directly, the bug
    will be filed on one of its products.
    """
    # It doesn't matter which product the bug is filed on.
    product = random.choice(list(project.products))
    bug = bugtarget_filebug(product, summary, status=status)
    return bug


def projectSetUp(test):
    """Setup the `IProject` test."""
    setUp(test)
    test.globs['bugtarget'] = getUtility(IProjectSet).getByName('mozilla')
    test.globs['filebug'] = project_filebug


def productseries_filebug(productseries, summary, status=None):
    """File a bug on a product series.

    Since it's not possible to file a bug on a product series directly,
    the bug will first be filed on its product, then a series task will
    be created.
    """
    bug = bugtarget_filebug(productseries.product, summary, status=status)
    getUtility(IBugTaskSet).createTask(
        bug, getUtility(ILaunchBag).user, productseries=productseries,
        status=status)
    return bug


def productSeriesSetUp(test):
    """Setup the `IProductSeries` test."""
    setUp(test)
    firefox = getUtility(IProductSet).getByName('firefox')
    test.globs['bugtarget'] = firefox.getSeries('trunk')
    test.globs['filebug'] = productseries_filebug


def distributionSetUp(test):
    """Setup the `IDistribution` test."""
    setUp(test)
    test.globs['bugtarget'] = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['filebug'] = bugtarget_filebug


def distributionSourcePackageSetUp(test):
    """Setup the `IDistributionSourcePackage` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['bugtarget'] = ubuntu.getSourcePackage('mozilla-firefox')
    test.globs['filebug'] = bugtarget_filebug


def distroseries_filebug(distroseries, summary, sourcepackagename=None,
                          status=None):
    """File a bug on a distroseries.

    Since bugs can't be filed on distroseriess directly, a bug will
    first be filed on its distribution, and then a series task will be
    added.
    """
    bug = bugtarget_filebug(distroseries.distribution, summary, status=status)
    getUtility(IBugTaskSet).createTask(
        bug, getUtility(ILaunchBag).user, distroseries=distroseries,
        sourcepackagename=sourcepackagename, status=status)
    return bug


def distributionSeriesSetUp(test):
    """Setup the `IDistroSeries` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    test.globs['bugtarget'] = ubuntu.getSeries('warty')
    test.globs['filebug'] = distroseries_filebug


def sourcepackage_filebug(source_package, summary, status=None):
    """File a bug on a source package in a distroseries."""
    bug = distroseries_filebug(
        source_package.distroseries, summary,
        sourcepackagename=source_package.sourcepackagename, status=status)
    return bug


def sourcePackageSetUp(test):
    """Setup the `ISourcePackage` test."""
    setUp(test)
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    warty = ubuntu.getSeries('warty')
    test.globs['bugtarget'] = warty.getSourcePackage('mozilla-firefox')
    test.globs['filebug'] = sourcepackage_filebug


def test_suite():
    """Return the `IBugTarget` TestSuite."""
    suite = unittest.TestSuite()

    setUpMethods = [
        productSetUp,
        productSeriesSetUp,
        projectSetUp,
        distributionSetUp,
        distributionSourcePackageSetUp,
        distributionSeriesSetUp,
        sourcePackageSetUp,
        ]

    for setUpMethod in setUpMethods:
        test = FunctionalDocFileSuite('bugtarget-bugcount.txt',
            setUp=setUpMethod, tearDown=tearDown,
            optionflags=default_optionflags, package=__name__,
            layer=LaunchpadFunctionalLayer)
        suite.addTest(test)
    return suite
