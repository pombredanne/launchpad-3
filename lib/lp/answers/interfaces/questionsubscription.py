# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Question subscription interface."""

__metaclass__ = type

__all__ = [
    'IQuestionSubscription',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )


class IQuestionSubscription(Interface):
    """A subscription for a person to a question."""

    person = Attribute("The subscriber.")
    question = Attribute("The question.")

