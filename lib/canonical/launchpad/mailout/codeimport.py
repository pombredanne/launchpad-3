# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Email notifications related to code imports."""

__metaclass__ = type


from zope.component import getUtility

from canonical.launchpad.helpers import (
    contactEmailAddresses, get_email_template)
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.mail import format_address, simple_sendmail
from canonical.launchpad.webapp import canonical_url


def new_import(code_import, event):
    """Email the vcs-imports team about a new code import."""
    if event.user is None:
        # If there is no logged in user, then we are most likely in a
        # test.
        return

    headers = {'X-Launchpad-Branch': code_import.branch.unique_name}
    subject = 'New code import: %s/%s' % (
        code_import.product.name, code_import.branch.name)
    body = get_email_template('new-code-import.txt') % {
        'person': code_import.registrant.displayname,
        'branch': canonical_url(code_import.branch)}

    from_address = format_address(
        event.user.displayname, event.user.preferredemail.email)

    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    for address in contactEmailAddresses(vcs_imports):
        simple_sendmail(from_address, address, subject, body, headers)

