# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests for the validators."""

__metaclass__ = type

from zope.component import getUtility
from zope.testing.doctest import DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS

from canonical.testing.layers import LaunchpadFunctionalLayer
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import (
    CreateBugParams, IOpenLaunchBag, IPersonSet, IProductSet)


def test_can_be_nominated_for_releases(self):
    """The can_be_nominated_for_releases() validator.

        >>> from canonical.launchpad.interfaces import (
        ...     can_be_nominated_for_releases)

    This validator is used to check if the bug in the launchbag can be
    nominated for the given series or releases.

    If we create a new bug, all the target's releases can be nominated.

        >>> login('no-priv@canonical.com')
        >>> no_priv = getUtility(IPersonSet).getByEmail(
        ...     'no-priv@canonical.com')
        >>> firefox = getUtility(IProductSet).getByName('firefox')
        >>> bug = firefox.createBug(
        ...     CreateBugParams(no_priv, "New Bug", comment="New Bug."))
        >>> getUtility(IOpenLaunchBag).add(bug)

        >>> can_be_nominated_for_releases(firefox.serieslist)
        True

    If we nominate the bug for one of the series, the validation will
    fail for that specific series.

        >>> nomination = bug.addNomination(no_priv, firefox.serieslist[0])
        >>> can_be_nominated_for_releases(firefox.serieslist)
        Traceback (most recent call last):
        ...
        LaunchpadValidationError...

        >>> can_be_nominated_for_releases([firefox.serieslist[0]])
        Traceback (most recent call last):
        ...
        LaunchpadValidationError...

    It will pass for the rest of the series, though.

        >>> can_be_nominated_for_releases(firefox.serieslist[1:])
        True

    Of course, if we accept the nomination, the validation will still
    fail:

        >>> login('foo.bar@canonical.com')
        >>> foo_bar =  getUtility(IPersonSet).getByEmail(
        ...     'foo.bar@canonical.com')
        >>> nomination.approve(foo_bar)
        >>> can_be_nominated_for_releases([firefox.serieslist[0]])
        Traceback (most recent call last):
        ...
        LaunchpadValidationError...

    The validation message will contain all the series that can't be
    nominated.

        >>> trunk_nomination = bug.addNomination(
        ...     no_priv, firefox.serieslist[1])
        >>> can_be_nominated_for_releases(firefox.serieslist)
        Traceback (most recent call last):
        ...
        LaunchpadValidationError:
        This bug has already been nominated for these releases: 1.0, Trunk

    The validation will still fail if a nomination is declined.

        >>> trunk_nomination.decline(foo_bar)
        >>> can_be_nominated_for_releases([firefox.serieslist[1]])
        Traceback (most recent call last):
        ...
        LaunchpadValidationError...
    """

def test_suite():
    suite = DocTestSuite(
        optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS)
    suite.layer = LaunchpadFunctionalLayer
    return suite

