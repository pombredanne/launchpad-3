# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Karma for the Answer Tracker / Bugs extension."""

__metaclass__ = type
__all__ = []

from lp.answers.karma import assignKarmaUsingQuestionContext
from lp.bugs.interfaces.bug import IBug
from lp.registry.interfaces.person import IPerson
from lp.services.database.sqlbase import block_implicit_flushes


@block_implicit_flushes
def question_bug_linked(questionbug, event):
    """Assign karma to the user which added <questionbug>."""
    if IBug.providedBy(event.other_object):
        assignKarmaUsingQuestionContext(
            IPerson(event.user), event.object, 'questionlinkedtobug')
