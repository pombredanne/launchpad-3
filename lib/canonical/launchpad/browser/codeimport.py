# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Docstring."""

__metaclass__ = type

__all__ = ['CodeImportSetView']


from zope.component import getUtility

from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView


class CodeImportSetView(LaunchpadView):
    def initialize(self):
        self.results = getUtility(ICodeImportSet).getAll()
