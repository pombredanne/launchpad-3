
#
# The Buttress application. Interface, view and context have all been put
# into this one file because they are trivial, they should be moved to
# distinct files.
#

from zope.interface import implements
from canonical.launchpad.interfaces import ILaunchpadApplication

class IButtressApplication(ILaunchpadApplication):
    """A Buttress Application"""


class ButtressApplication:
    implements(IButtressApplication)

class ButtressApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


