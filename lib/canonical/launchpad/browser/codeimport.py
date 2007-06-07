# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Broswer views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    ]


from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView, Navigation
from canonical.launchpad.webapp.batching import BatchNavigator


class CodeImportSetNavigation(Navigation):

    usedfor = ICodeImportSet

    def breadcrumb(self):
        return "Code Imports"

    def traverse(self, name):
        return self.context.getByName(name)

class CodeImportSetView(LaunchpadView):
    def initialize(self):
        self.batchnav = BatchNavigator(
            self.context.getAll(), self.request, size=50)
