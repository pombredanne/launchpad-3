# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = [
    'can_be_nominated_for_series',
    'non_duplicate_branch',
    'valid_bug_number',
    'valid_cve_sequence',
    'validate_new_team_email',
    'validate_new_person_email',
    'valid_password',
    'validate_date_interval',
    ]

from cgi import escape
from textwrap import dedent

from zope.app.form.interfaces import WidgetsError
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces.emailaddress import (
    IEmailAddressSet,
    )
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.menu import structured
from lp.app.errors import NotFoundError
from lp.app.validators import LaunchpadValidationError
from lp.app.validators.cve import valid_cve
from lp.app.validators.email import valid_email


def can_be_nominated_for_series(series):
    """Can the bug be nominated for these series?"""
    current_bug = getUtility(ILaunchBag).bug
    unnominatable_series = []
    for s in series:
        if not current_bug.canBeNominatedFor(s):
            unnominatable_series.append(s.name.capitalize())

    if unnominatable_series:
        series_str = ", ".join(unnominatable_series)
        raise LaunchpadValidationError(_(
            "This bug has already been nominated for these "
            "series: ${series}", mapping={'series': series_str}))

    return True


def non_duplicate_branch(value):
    """Ensure that this branch hasn't already been linked to this bug."""
    current_bug = getUtility(ILaunchBag).bug
    if current_bug.hasBranch(value):
        raise LaunchpadValidationError(_(dedent("""
            This branch is already registered on this bug.
            """)))

    return True


def valid_bug_number(value):
    from lp.bugs.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    try:
        bugset.get(value)
    except NotFoundError:
        raise LaunchpadValidationError(_(
            "Bug ${bugid} doesn't exist.", mapping={'bugid': value}))
    return True


def valid_cve_sequence(value):
    """Check if the given value is a valid CVE otherwise raise an exception.
    """
    if valid_cve(value):
        return True
    else:
        raise LaunchpadValidationError(_(
            "${cve} is not a valid CVE number", mapping={'cve': value}))


def _validate_email(email):
    if not valid_email(email):
        raise LaunchpadValidationError(_(
            "${email} isn't a valid email address.",
            mapping={'email': email}))


def _check_email_availability(email):
    email_address = getUtility(IEmailAddressSet).getByEmail(email)
    if email_address is not None:
        # The email already exists; determine what has it.
        if email_address.person is not None:
            person = email_address.person
            message = _('${email} is already registered in Launchpad and is '
                        'associated with <a href="${url}">${person}</a>.',
                        mapping={'email': escape(email),
                                'url': canonical_url(person),
                                'person': escape(person.displayname)})
        elif email_address.account is not None:
            account = email_address.account
            message = _('${email} is already registered in Launchpad and is '
                        'associated with the ${account} account.',
                        mapping={'email': escape(email),
                                'account': escape(account.displayname)})
        else:
            message = _('${email} is already registered in Launchpad.',
                        mapping={'email': escape(email)})
        raise LaunchpadValidationError(structured(message))


def validate_new_team_email(email):
    """Check that the given email is valid and not registered to
    another launchpad account.
    """
    _validate_email(email)
    _check_email_availability(email)
    return True


def validate_new_person_email(email):
    """Check that the given email is valid and not registered to
    another launchpad account.

    This validator is supposed to be used only when creating a new profile
    using the /people/+newperson page, as the message will say clearly to the
    user that the profile he's trying to create already exists, so there's no
    need to create another one.
    """
    from canonical.launchpad.webapp.publisher import canonical_url
    from lp.registry.interfaces.person import IPersonSet
    _validate_email(email)
    owner = getUtility(IPersonSet).getByEmail(email)
    if owner is not None:
        message = _("The profile you're trying to create already exists: "
                    '<a href="${url}">${owner}</a>.',
                    mapping={'url': canonical_url(owner),
                             'owner': escape(owner.displayname)})
        raise LaunchpadValidationError(structured(message))
    return True


def valid_password(password):
    """Return True if the argument is a valid password.

    A valid password contains only ASCII characters in range(32,127).
    No ASCII control characters are allowed.

    password that contains only valid ASCII characters
    >>> valid_password(u"All ascii password with spaces.:\\&/")
    True

    password that contains some non-ASCII character (value > 127)
    >>> valid_password(u"password with some non-ascii" + unichr(195))
    False

    password that contains ASCII control characters (0 >= value >= 31)
    >>> valid_password(u"password with control chars" + chr(20))
    False

    empty password.
    >>> valid_password(u"")
    True

    """
    assert isinstance(password, unicode)
    valid_chars = [chr(x) for x in range(32, 127)]
    invalid = set(password) - set(valid_chars)
    if invalid:
        return False
    else:
        return True


def validate_date_interval(start_date, end_date, error_msg=None):
    """Check if start_date precedes end_date.

    >>> from datetime import datetime
    >>> start = datetime(2006, 7, 18)
    >>> end = datetime(2006, 8, 18)
    >>> validate_date_interval(start, end)
    >>> validate_date_interval(end, start)
    Traceback (most recent call last):
    ...
    WidgetsError: LaunchpadValidationError: This event can't start after it
    ends.
    >>> validate_date_interval(end, start, error_msg="A custom error msg")
    Traceback (most recent call last):
    ...
    WidgetsError: LaunchpadValidationError: A custom error msg

    """
    if error_msg is None:
        error_msg = _("This event can't start after it ends.")
    if start_date >= end_date:
        raise WidgetsError([LaunchpadValidationError(error_msg)])
