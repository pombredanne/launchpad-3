
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')
from zope.interface import Interface

class IMaloneApplication(Interface):
    """Malone application class."""


