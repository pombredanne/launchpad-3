# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Interfaces for objects that can be linked to bugs."""

__metaclass__ = type

__all__ = [
    'IBugLink',
    'IBugLinkForm',
    'IBugLinkTarget',
    'IUnlinkBugsForm',
    ]

from zope.interface import implements, Interface
from zope.schema import Choice, List, Object, Set
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.fields import BugField
from canonical.launchpad.interfaces.bug import IBug
from canonical.launchpad.interfaces.launchpad import IHasBug


class IBugLink(IHasBug):
    """An entity representing a link between a bug and its target."""

    bug = BugField(title=_("The bug that is linked to."), required=True,
                   readonly=True)

    target = Object(title=_("The object to which the bug is linked."),
                    required=True, readonly=True, schema=Interface)


class IBugLinkTarget(Interface):
    """An entity which can be linked to a bug.

    Examples include an IQuestion, and an ICve.
    """

    bugs = List(title=_("Bugs related to this object."),
                value_type=Object(schema=IBug), readonly=True)
    bug_links = List(title=_("The links between bugs and this object."),
                     value_type=Object(schema=IBugLink), readonly=True)

    def linkBug(bug):
        """Link the object with this bug. If the object is already linked,
        return the old linker, otherwise return a new IBugLink object.

        If a new IBugLink is created by this method, a SQLObjectCreatedEvent
        should be sent.
        """

    def unlinkBug(bug):
        """Remove any link between this object and the bug. If the bug wasn't
        linked to the target, returns None otherwise returns the IBugLink
        object which was removed.

        If an IBugLink is removed by this method, a SQLObjectDeletedEvent
        should be sent.
        """


# These schemas are only used by browser/buglinktarget.py and should really
# live there. See Bug #66950.
class IBugLinkForm(Interface):
    """Schema for the unlink bugs form."""

    bug = BugField(
        title=_('Bug ID'), required=True)


# XXX flacoste 2006-08-29: To remain consistent with the existing source
# code layout policy, this should really be in vocabularies.buglinks but this
# is not possible because of dependencies on interfaces in some vocabularies
# modules.
class BugLinksVocabularyFactory:
    """IContextSourceBinder that creates a vocabulary of the linked bugs on
    the IBugLinkTarget.
    """

    implements(IContextSourceBinder)

    def __call__(self, context):
        """See IContextSourceBinder."""
        terms = []
        for bug in context.bugs:
            try:
                title = _(
                    '#${bugid}: ${title}',
                    mapping={'bugid': bug.id, 'title': bug.title})
                terms.append(SimpleTerm(bug, bug.id, title))
            except Unauthorized:
                pass
        return SimpleVocabulary(terms)


class IUnlinkBugsForm(Interface):
    """Schema for the unlink bugs form."""

    bugs = Set(title=_('Bug Links'), required=True,
               value_type=Choice(source=BugLinksVocabularyFactory()),
               description=_('Select the bug links that you want to remove.'))
