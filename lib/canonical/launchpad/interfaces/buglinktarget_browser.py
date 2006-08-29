# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Schemas for IBugLinkTarget browser forms.

XXX flacoste 2006/08/29 This is in the interfaces package just
to comply with the existing policy. These schemas are only used
by browser/buglinktarget.py and should really live there.
"""

__metaclass__ = type

__all__ = [
    'IBugLinkForm',
    'IUnlinkBugsForm',
    ]

from zope.interface import implements, Interface
from zope.schema import Choice, Set
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.security.interfaces import Unauthorized

from canonical.launchpad import _
from canonical.launchpad.fields import BugField

class IBugLinkForm(Interface):
    """Schema for the unlink bugs form."""

    bug = BugField(
        title=_('Bug ID'), required=True,
        description=_("Enter the Malone bug ID or nickname that "
                      "you want to link to."))

# XXX flacoste 2006/08/29 To spread things apart while remaining consistent
# with the existing source code layout policy, this should really be
# in vocabularies.buglinks but this is not possible because of dependencies
# interfaces in some vocabularies modules.
class BugLinksVocabularyFactory(object):
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

    bugs = Set(title=_('Bug Links:'), required=True,
               value_type=Choice(source=BugLinksVocabularyFactory()),
               description=_('Select the bug links that you want to remove.'))

