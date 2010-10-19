# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Branch merge queue interfaces."""

__metaclass__ = type

__all__ = [
    'IBranchMergeQueue',
    'IBranchMergeQueueSource',
    ]

from lazr.restful.declarations import (
    export_as_webservice_entry,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface
from zope.schema import (
    Datetime,
    Int,
    Text,
    TextLine,
    )

from canonical.launchpad import _
from lp.services.fields import (
    PersonChoice,
    PublicPersonChoice,
    )


class IBranchMergeQueue(Interface):
    """An interface for managing branch merges."""

    export_as_webservice_entry()

    id = Int(title=_('ID'), readonly=True, required=True)

    registrant = PublicPersonChoice(
        title=_("The user that registered the branch."),
        required=True, readonly=True,
        vocabulary='ValidPersonOrTeam')

    owner = PersonChoice(
        title=_('Owner'),
        required=True, readonly=True,
        vocabulary='UserTeamsParticipationPlusSelf',
        description=_("The owner of the merge queue."))

    name = TextLine(
        title=_('Name'), required=True,
        description=_(
            "Keep very short, unique, and descriptive, because it will "
            "be used in URLs.  "
            "Examples: main, devel, release-1.0, gnome-vfs."))

    description = Text(
        title=_('Description'), required=False,
        description=_(
            'A short description of the purpose of this merge queue.'))

    configuration = TextLine(
        title=_('Configuration'), required=False,
        description=_(
            "A JSON string of configuration values."))

    date_created = Datetime(
        title=_('Date Created'),
        required=True,
        readonly=True)

    branches = CollectionField(
        title=_('Dependent Branches'),
        description=_('A collection of branches that this queue manages.'),
        readonly=True,
        value_type=Reference(Interface))

    def setMergeQueueConfig(config):
        """Set the JSON string configuration of the merge queue.

        :param config: A JSON string of configuration values.
        """


class IBranchMergeQueueSource(Interface):

    def new(name, owner, registrant, description, configuration, branches):
        """Create a new IBranchMergeQueue object.

        :param name: The name of the branch merge queue.
        :param description: A description of queue.
        :param configuration: A JSON string of configuration values.
        :param owner: The owner of the queue.
        :param registrant: The registrant of the queue.
        :param branches: A list of branches to add to the queue.
        """
