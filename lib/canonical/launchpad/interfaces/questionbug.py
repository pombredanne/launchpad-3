# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Interfaces for linking between an IQuestion and an IBug."""

__metaclass__ = type

__all__ = [
    'IQuestionBug',
    ]

from zope.schema import Object

from canonical.launchpad import _
from canonical.launchpad.interfaces.buglink import IBugLink
from canonical.launchpad.interfaces.question import IQuestion

class IQuestionBug(IBugLink):
    """A link between an IBug and an IQuestion."""

    question = Object(title=_('The question to which the bug is linked to.'),
        required=True, readonly=True, schema=IQuestion)
