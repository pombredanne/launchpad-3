from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface
from zope.schema import Choice, TextLine

from canonical.launchpad.interfaces import IHasProduct

class IMilestone(IHasProduct):
    product = Choice(
        title = _("Product"),
        description = _("The product to which this milestone is associated"),
        required = True, values = ('foo',))
    name = TextLine(title = _("Name"), required = True)
    title = TextLine(title = _("Title"), required = True)

class IMilestoneSet(Interface):
    def __iter__():
        """Return an iterator over all the milestones for a thing."""

    def __getitem__(name):
        """Get a milestone by its name."""
