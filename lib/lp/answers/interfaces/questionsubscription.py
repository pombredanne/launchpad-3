# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Question subscription interface."""

__metaclass__ = type

__all__ = [
    'IQuestionSubscription',
    ]

from zope.interface import Interface, Attribute

class IQuestionSubscription(Interface):
    """A subscription for a person to a question."""

    person = Attribute("The subscriber.")
    question = Attribute("The question.")

