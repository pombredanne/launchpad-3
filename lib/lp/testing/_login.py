# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# We like global statements!
# pylint: disable-msg=W0602,W0603
__metaclass__ = type

from zope.security.management import endInteraction
from canonical.launchpad.webapp.interaction import (
    setupInteractionByEmail, setupInteractionForPerson)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.vhosts import allvhosts

__all__ = [
    'login',
    'login_person',
    'logout',
    'is_logged_in']


_logged_in = False

def is_logged_in():
    global _logged_in
    return _logged_in


def _test_login_impl(participation):
    # Common implementation of the test login wrappers.
    # It sets the global _logged_in flag and create a default
    # participation if None was specified.
    global _logged_in
    _logged_in = True

    if participation is None:
        # we use the main site as the host name.  This is a guess, to make
        # canonical_url produce a real-looking host name rather than
        # 127.0.0.1.
        participation = LaunchpadTestRequest(
            environ={'HTTP_HOST': allvhosts.configs['mainsite'].hostname,
                     'SERVER_URL': allvhosts.configs['mainsite'].rooturl})
    return participation


def login(email, participation=None):
    """Simulates a login, using the specified email.

    If the canonical.launchpad.ftests.ANONYMOUS constant is supplied
    as the email, you'll be logged in as the anonymous user.

    You can optionally pass in a participation to be used.  If no
    participation is given, a LaunchpadTestRequest is used.

    If the participation provides IPublicationRequest, it must implement
    setPrincipal(), otherwise it must allow setting its principal attribute.
    """

    participation = _test_login_impl(participation)
    setupInteractionByEmail(email, participation)


def login_person(person, participation=None):
    """Login the person with their preferred email."""
    participation = _test_login_impl(participation)
    setupInteractionForPerson(person, participation)


def logout():
    """Tear down after login(...), ending the current interaction.

    Note that this is done automatically in
    canonical.launchpad.ftest.LaunchpadFunctionalTestCase's tearDown method so
    you generally won't need to call this.
    """
    global _logged_in
    _logged_in = False
    endInteraction()
