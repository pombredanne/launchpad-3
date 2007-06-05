# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Broswer views for CodeImports."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    'CodeImportView',
    ]


from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView, Navigation


class CodeImportSetNavigation(Navigation):

    usedfor = ICodeImportSet

    def breadcrumb(self):
        return "Code Imports"

    def traverse(self, name):
        return self.context.getByName(name)

class CodeImportSetView(LaunchpadView):
    pass

class CodeImportView(LaunchpadView):
    pass
