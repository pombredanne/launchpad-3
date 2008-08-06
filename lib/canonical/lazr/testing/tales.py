# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Helper functions for testing TALES expressions."""

__metaclass__ = type

__all__ = [
    'test_tales',
    ]

from zope.app.pagetemplate.engine import Engine


class Context:
    """A simple TALES context that only contains specified values."""
    def __init__(self, **kw):
        self.vars = kw
        self.contexts = kw


def test_tales(expression, **kw):
    """Return the evaluation of the expression.

    :param expression: The TALES expression to evaluate.
    :param kw: all variables that are defined in the context.
    :return: the evaluated expression.
    """
    compiled_tales = Engine.compile(expression)
    return compiled_tales(Context(**kw))

