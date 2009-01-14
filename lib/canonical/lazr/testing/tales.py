# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Helper functions for testing TALES expressions."""

__metaclass__ = type

__all__ = [
    'test_tales',
    ]

from zope.app.pagetemplate.engine import TrustedEngine


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
    # XXX sinzui 2008-09-29 bug=276120:
    # We need to review the security policy regarding launchpad use of
    # tales. The non-trusted pagetemplate.engine.Engine will rightly
    # fail if an object is accessed or imported outside of page's namespace.
    compiled_tales = TrustedEngine.compile(expression)
    return compiled_tales(Context(**kw))

