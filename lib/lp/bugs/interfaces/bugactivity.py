# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Bug activity interfaces."""

__metaclass__ = type

__all__ = [
    'IBugActivity',
    'IBugActivitySet',
    ]

from zope.interface import Interface
from zope.schema import (
    Datetime,
    Text,
    TextLine,
    )

from lazr.restful.declarations import (
    export_as_webservice_entry,
    exported,
    )

from lp.services.fields import (
    BugField,
    PersonChoice,
    )

from canonical.launchpad import _


class IBugActivity(Interface):
    """A log of all things that have happened to a bug."""
    export_as_webservice_entry()

    bug = exported(
        BugField(title=_('Bug'), readonly=True))

    datechanged = exported(
        Datetime(title=_('Date Changed'),
                 description=_("The date on which this activity occurred."),
                 readonly=True))

    person = exported(PersonChoice(
        title=_('Person'), required=True, vocabulary='ValidPersonOrTeam',
        readonly=True, description=_("The person's Launchpad ID or "
        "e-mail address.")))

    whatchanged = exported(
        TextLine(title=_('What Changed'),
                 description=_("The property of the bug that changed."),
                 readonly=True))

    target = TextLine(
        title=_('Change Target'), required=False, readonly=True,
        description=_(
            'The target of what changed, if the change occurred on a '
            'bugtask.'))

    attribute = TextLine(
        title=_('Changed Attribute'), required=True, readonly=True,
        description=_(
            "The attribute that changed.  If the change occurred on a "
            "bugtask, this will be the bugtask's attribute; otherwise "
            "it will be the bug attribute, and the same as 'what "
            "changed'."))

    oldvalue = exported(
        TextLine(title=_('Old Value'),
                 description=_("The value before the change."),
                 readonly=True))

    newvalue = exported(
        TextLine(title=_('New Value'),
                 description=_("The value after the change."),
                 readonly=True))

    message = exported(
        Text(title=_('Message'),
             description=_("Additional information about what changed."),
             readonly=True))


class IBugActivitySet(Interface):
    """The set of all bug activities."""

    def new(bug, datechanged, person, whatchanged,
            oldvalue=None, newvalue=None, message=None):
        """Creates a new log of what happened to a bug and returns it."""
