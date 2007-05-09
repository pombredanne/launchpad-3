# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Answer contact interfaces."""

__metaclass__ = type

__all__ = [
    'IAnswerContact',
    ]


from zope.interface import Interface, Attribute
from zope.schema import Bool, Choice

from canonical.launchpad import _


class IAnswerContact(Interface):
    """An answer contact.

    That's a person willing to receive notifications about all questions
    in a particular context.
    """

    person = Choice(title=_('Answer Contact'), required=False,
        description=_(
            "The person receiving notifications about all questions."),
        vocabulary='ValidPersonOrTeam')
    product = Choice(title=_('Project'), required=False,
        description=_(
            "The person wants to receive notifications about this project's "
            "questions."),
        vocabulary='Product')

    distribution = Choice(title=_('Distribution'), required=False,
        description=_(
            "The person wants to receive notifications about this "
            "distribution's questions."),
        vocabulary='Distribution')

    sourcepackagename = Choice(title=_('Source Package'), required=False,
        description=_(
            "The person wants to receive notifications about this "
            "sourcepackage's questions."),
        vocabulary='SourcePackageName')
        
    limited_languages = Bool(title=_("Preferred Languages Only"),
        required=False, default=False, 
        description=_("The person wants to be notified of questions in his "
            "preferred languages only."))
