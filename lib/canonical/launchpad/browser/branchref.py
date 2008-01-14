# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser code used to implement virtual '.bzr' directories."""

__metaclass__ = type
__all__ = [
    'BranchRef'
    ]

from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.config import config
from canonical.launchpad.interfaces import IBranchRef
from canonical.launchpad.webapp import Navigation, stepto, stepthrough


class BranchRef:
    implements(IBranchRef)

    def __init__(self, branch):
        self.branch = branch


# XXX jamesh 2006-09-26:
# Eventually we will be able to change this to serve a simple HTTP
# redirect for 'branch-format' and have bzr do the rest.  However,
# current Bazaar releases would continue to request branch data files
# at this location.
#
# Synthesising a branch reference provides the desired behaviour with
# current Bazaar releases, however.

class BranchRefNavigation(Navigation):

    usedfor = IBranchRef

    @stepto('branch-format')
    def branch_format(self):
        return StaticContentView('Bazaar-NG meta directory, format 1\n')

    @stepthrough('branch')
    def traverse_branch(self, name):
        if name == 'format':
            return StaticContentView('Bazaar-NG Branch Reference Format 1\n')
        elif name == 'location':
            return StaticContentView(config.codehosting.supermirror_root +
                                     self.context.branch.unique_name)
        else:
            return None


class StaticContentView:
    implements(IBrowserPublisher)

    def __init__(self, contents):
        self.contents = contents

    def __call__(self):
        return self.contents

    def browserDefault(self, request):
        return self, ()
