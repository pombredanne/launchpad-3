# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for linking between an IQuestion and an IBug."""

__metaclass__ = type

__all__ = [
    'IQuestionBug',
    ]

from zope.schema import Object

from canonical.launchpad import _
from lp.answers.interfaces.question import IQuestion
from lp.bugs.interfaces.buglink import IBugLink


class IQuestionBug(IBugLink):
    """A link between an IBug and an IQuestion."""

    question = Object(title=_('The question to which the bug is linked to.'),
        required=True, readonly=True, schema=IQuestion)
