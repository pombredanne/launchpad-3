# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for rendering the time out OOPS page."""

__metaclass__ = type

__all__ = [
    'test_suite',
    ]


from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer


def test_suite():
    suite = LayeredDocFileSuite(
            'test_request_expire_render.txt',
            layer=LaunchpadFunctionalLayer, setUp=setUp, tearDown=tearDown,
            )
    return suite

