
#
# The Bazaar application. Interface, view and context have all been put
# into this one file because they are trivial, they should be moved to
# distinct files.
#

from zope.interface import implements
from canonical.launchpad.interfaces import ILaunchpadApplication

class IBazaarApplication(ILaunchpadApplication):
    """A Bazaar Application"""


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'

class BazaarApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


