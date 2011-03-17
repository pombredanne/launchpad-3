# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import logging
import os

import transaction

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    DatabaseLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.tests import mailinglists_helper
from lp.services.testing import (
    build_doctest_suite,
    build_test_suite,
    )


here = os.path.dirname(os.path.realpath(__file__))


def peopleKarmaTearDown(test):
    """Restore the database after testing karma."""
    # We can't detect db changes made by the subprocess (yet).
    DatabaseLayer.force_dirty_database()
    tearDown(test)


def mailingListXMLRPCInternalSetUp(test):
    setUp(test)
    mailinglist_api = mailinglists_helper.MailingListXMLRPCTestProxy(
        context=None, request=None)
    test.globs['mailinglist_api'] = mailinglist_api
    test.globs['commit'] = transaction.commit


def mailingListXMLRPCExternalSetUp(test):
    setUp(test)
    # Use a real XMLRPC server proxy so that the same test is run through the
    # full security machinery.  This is more representative of the real-world,
    # but more difficult to debug.
    from lp.testing.xmlrpc import XMLRPCTestTransport
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
    'distribution-mirror.txt': LayeredDocFileSuite(
        '../doc/distribution-mirror.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
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
    'product.txt': LayeredDocFileSuite(
        '../doc/product.txt',
        setUp=setUp,
        tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'private-team-roles.txt': LayeredDocFileSuite(
        '../doc/private-team-roles.txt',
        setUp=setUp,
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
    'karmacache.txt': LayeredDocFileSuite(
        '../doc/karmacache.txt',
        layer=LaunchpadZopelessLayer,
        setUp=setUp, tearDown=tearDown),
    'sourcepackage.txt': LayeredDocFileSuite(
        '../doc/sourcepackage.txt',
        layer=LaunchpadFunctionalLayer,
        setUp=setUp, tearDown=tearDown),
    'distribution-sourcepackage.txt': LayeredDocFileSuite(
        '../doc/distribution-sourcepackage.txt',
        layer=LaunchpadZopelessLayer,
        setUp=setUp, tearDown=tearDown),
    }


def test_suite():
    suite = build_test_suite(here, special, layer=DatabaseFunctionalLayer)
    launchpadlib_path = os.path.join(os.path.pardir, 'doc', 'launchpadlib')
    lplib_suite = build_doctest_suite(here, launchpadlib_path,
                                      layer=DatabaseFunctionalLayer)
    suite.addTest(lplib_suite)
    return suite
