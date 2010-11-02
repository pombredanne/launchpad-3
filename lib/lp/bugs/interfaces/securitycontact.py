# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Security contact interfaces."""

__metaclass__ = type

__all__ = [
    'IHasSecurityContact',
    ]

from lazr.restful.declarations import exported
from zope.interface import Interface

from canonical.launchpad import _
from lp.services.fields import PublicPersonChoice


class IHasSecurityContact(Interface):
    """An object that has a security contact."""

    security_contact = exported(PublicPersonChoice(
        title=_("Security Contact"),
        description=_(
            "The Launchpad id of the person or team (preferred) who handles "
            "security-related bug reports.  The security contact will be "
            "subscribed to all bugs marked as a security vulnerability and "
            "will receive email about all activity on all security bugs."),
        required=False, vocabulary='ValidPersonOrTeam'))
