# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
Run the doctests and pagetests.
"""

import logging
import os
import transaction
import unittest

from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import (
    DatabaseLayer, DatabaseFunctionalLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer)

from lp.registry.tests import mailinglists_helper


here = os.path.dirname(os.path.realpath(__file__))


def peopleKarmaTearDown(test):
    """Restore the database after testing karma."""
    # We can't detect db changes made by the subprocess (yet).
    DatabaseLayer.force_dirty_database()
    tearDown(test)

def mailingListXMLRPCInternalSetUp(test):
    setUp(test)
    # Use the direct API view instance, not retrieved through the component
    # architecture.  Don't use ServerProxy.  We do this because it's easier to
    # debug because when things go horribly wrong, you see the errors on
    # stdout instead of in an OOPS report living in some log file somewhere.
    from canonical.launchpad.xmlrpc import MailingListAPIView
    class ImpedenceMatchingView(MailingListAPIView):
        @mailinglists_helper.fault_catcher
        def getPendingActions(self):
            return super(ImpedenceMatchingView, self).getPendingActions()
        @mailinglists_helper.fault_catcher
        def reportStatus(self, statuses):
            return super(ImpedenceMatchingView, self).reportStatus(statuses)
        @mailinglists_helper.fault_catcher
        def getMembershipInformation(self, teams):
            return super(
                ImpedenceMatchingView, self).getMembershipInformation(teams)
        @mailinglists_helper.fault_catcher
        def isLaunchpadMember(self, address):
            return super(ImpedenceMatchingView, self).isLaunchpadMember(
                address)
        @mailinglists_helper.fault_catcher
        def isTeamPublic(self, team_name):
            return super(ImpedenceMatchingView, self).isTeamPublic(team_name)
    # Expose in the doctest's globals, the view as the thing with the
    # IMailingListAPI interface.  Also expose the helper functions.
    mailinglist_api = ImpedenceMatchingView(context=None, request=None)
    test.globs['mailinglist_api'] = mailinglist_api
    test.globs['commit'] = transaction.commit


def mailingListXMLRPCExternalSetUp(test):
    setUp(test)
    # Use a real XMLRPC server proxy so that the same test is run through the
    # full security machinery.  This is more representative of the real-world,
    # but more difficult to debug.
    from canonical.functional import XMLRPCTestTransport
    from xmlrpclib import ServerProxy
    mailinglist_api = ServerProxy(
        'http://xmlrpc-private.launchpad.dev:8087/mailinglists/',
        transport=XMLRPCTestTransport())
    test.globs['mailinglist_api'] = mailinglist_api
    # See above; right now this is the same for both the internal and external
    # tests, but if we're able to resolve the big XXX above the
    # mailinglist-xmlrpc.txt-external declaration below, I suspect that these
    # two globals will end up being different functions.
    test.globs['mailinglist_api'] = mailinglist_api
    test.globs['commit'] = transaction.commit


special = {
    'person-karma.txt': LayeredDocFileSuite(
        '../doc/person-karma.txt',
        setUp=setUp, tearDown=peopleKarmaTearDown,
        layer=LaunchpadFunctionalLayer,
        stdout_logging_level=logging.WARNING
        ),
    'mailinglist-xmlrpc.txt': LayeredDocFileSuite(
        '../doc/mailinglist-xmlrpc.txt',
        setUp=mailingListXMLRPCInternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer
        ),
    'mailinglist-xmlrpc.txt-external': LayeredDocFileSuite(
        '../doc/mailinglist-xmlrpc.txt',
        setUp=mailingListXMLRPCExternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'mailinglist-subscriptions-xmlrpc.txt': LayeredDocFileSuite(
        '../doc/mailinglist-subscriptions-xmlrpc.txt',
        setUp=mailingListXMLRPCInternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer
        ),
    'mailinglist-subscriptions-xmlrpc.txt-external': LayeredDocFileSuite(
        '../doc/mailinglist-subscriptions-xmlrpc.txt',
        setUp=mailingListXMLRPCExternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'message-holds.txt': LayeredDocFileSuite(
        '../doc/message-holds.txt',
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'message-holds-xmlrpc.txt': LayeredDocFileSuite(
        '../doc/message-holds-xmlrpc.txt',
        setUp=mailingListXMLRPCInternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer
        ),
    'message-holds-xmlrpc.txt-external': LayeredDocFileSuite(
        '../doc/message-holds-xmlrpc.txt',
        setUp=mailingListXMLRPCExternalSetUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'productrelease.txt': LayeredDocFileSuite(
        '../doc/productrelease.txt',
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'productrelease-file-download.txt': LayeredDocFileSuite(
        '../doc/productrelease-file-download.txt',
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'standing.txt': LayeredDocFileSuite(
        '../doc/standing.txt',
        layer=LaunchpadZopelessLayer,
        setUp=setUp, tearDown=tearDown,
        ),
    'sourceforge-remote-products.txt': LayeredDocFileSuite(
        '../doc/sourceforge-remote-products.txt',
        layer=LaunchpadZopelessLayer,
        ),
    'karmacache.txt': LayeredDocFileSuite(
        '../doc/karmacache.txt',
        layer=LaunchpadZopelessLayer,
        setUp=setUp, tearDown=tearDown),
    }


def test_suite():
    suite = unittest.TestSuite()

    stories_dir = os.path.join(os.path.pardir, 'stories')
    suite.addTest(PageTestSuite(stories_dir))
    stories_path = os.path.join(here, stories_dir)
    for story_dir in os.listdir(stories_path):
        full_story_dir = os.path.join(stories_path, story_dir)
        if not os.path.isdir(full_story_dir):
            continue
        story_path = os.path.join(stories_dir, story_dir)
        suite.addTest(PageTestSuite(story_path))

    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, os.path.pardir, 'doc'))
        )

    # Add special needs tests
    for key in sorted(special):
        special_suite = special[key]
        suite.addTest(special_suite)

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.endswith('.txt') and filename not in special]
    # Sort the list to give a predictable order.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=DatabaseFunctionalLayer,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite
