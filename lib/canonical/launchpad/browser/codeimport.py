# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Docstring."""

__metaclass__ = type

__all__ = [
    'CodeImportSetNavigation',
    'CodeImportSetView',
    'CodeImportView',
    ]


from zope.component import getUtility

from canonical.launchpad.interfaces import ICodeImportSet
from canonical.launchpad.webapp import LaunchpadView, Navigation


class CodeImportSetNavigation(Navigation):

    usedfor = ICodeImportSet

    def breadcrumb(self):
        return "Code Imports"

    def traverse(self, name):
        # XXX ICodeImportSet needs extending yes, why do you ask?
        imps = [ci for ci in self.context.getAll() if ci.name == name]
        if len(imps) != 1:
            return None
        else:
            return imps[0]

class CodeImportSetView(LaunchpadView):
    pass

class CodeImportView(LaunchpadView):
    pass
