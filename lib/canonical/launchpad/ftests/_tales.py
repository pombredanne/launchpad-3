# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Helper functions for testing TALES expressions."""

__metaclass__ = type

from zope.app.pagetemplate.engine import Engine

class Context:
    def __init__(self, **kw):
        self.vars = kw

def test_tales(expression, **kw):
    compiled_tales = Engine.compile(expression)
    return compiled_tales(Context(**kw))

