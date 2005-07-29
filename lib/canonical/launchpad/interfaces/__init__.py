# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import Interface, Attribute
from persistent import IPersistent

#
# Please DO NOT put interfaces here. put them in the correct
# file, one of person, project, bug, etc.
#
from canonical.launchpad.interfaces.launchpad import *

from canonical.launchpad.interfaces.archuser import *
from canonical.launchpad.interfaces.binarypackage import *
from canonical.launchpad.interfaces.binarypackagename import *
from canonical.launchpad.interfaces.bounty import *
from canonical.launchpad.interfaces.bountysubscription import *
from canonical.launchpad.interfaces.bugactivity import *
from canonical.launchpad.interfaces.bugattachment import *
from canonical.launchpad.interfaces.bugextref import *
from canonical.launchpad.interfaces.bug import *
from canonical.launchpad.interfaces.bugmessage import *
from canonical.launchpad.interfaces.bugsubscription import *
from canonical.launchpad.interfaces.bugtask import *
from canonical.launchpad.interfaces.bugtracker import *
from canonical.launchpad.interfaces.bugwatch import *
from canonical.launchpad.interfaces.build import *
from canonical.launchpad.interfaces.codeofconduct import *
from canonical.launchpad.interfaces.component import *
from canonical.launchpad.interfaces.country import *
from canonical.launchpad.interfaces.cveref import *
from canonical.launchpad.interfaces.distribution import *
from canonical.launchpad.interfaces.distroarchrelease import *
from canonical.launchpad.interfaces.distrorelease import *
from canonical.launchpad.interfaces.distroreleaselanguage import *
from canonical.launchpad.interfaces.files import *
from canonical.launchpad.interfaces.general import *
from canonical.launchpad.interfaces.geoip import *
from canonical.launchpad.interfaces.gpg import *
from canonical.launchpad.interfaces.gpghandler import *
from canonical.launchpad.interfaces.infestation import *
from canonical.launchpad.interfaces.irc import *
from canonical.launchpad.interfaces.jabber import *
from canonical.launchpad.interfaces.karma import *
from canonical.launchpad.interfaces.language import *
from canonical.launchpad.interfaces.launchpad import *
from canonical.launchpad.interfaces.launchpadstatistic import *
from canonical.launchpad.interfaces.librarian import *
from canonical.launchpad.interfaces.logintoken import *
from canonical.launchpad.interfaces.mail import *
from canonical.launchpad.interfaces.mailbox import *
from canonical.launchpad.interfaces.maintainership import *
from canonical.launchpad.interfaces.manifestentry import *
from canonical.launchpad.interfaces.manifest import *
from canonical.launchpad.interfaces.message import *
from canonical.launchpad.interfaces.milestone import *
from canonical.launchpad.interfaces.package import *
from canonical.launchpad.interfaces.packaging import *
from canonical.launchpad.interfaces.pathlookup import *
from canonical.launchpad.interfaces.person import *
from canonical.launchpad.interfaces.poexport import *
from canonical.launchpad.interfaces.pofile import *
from canonical.launchpad.interfaces.poll import *
from canonical.launchpad.interfaces.pomsgid import *
from canonical.launchpad.interfaces.pomsgidsighting import *
from canonical.launchpad.interfaces.pomsgset import *
from canonical.launchpad.interfaces.poparser import *
from canonical.launchpad.interfaces.potemplate import *
from canonical.launchpad.interfaces.potemplatename import *
from canonical.launchpad.interfaces.potmsgset import *
from canonical.launchpad.interfaces.potranslation import *
from canonical.launchpad.interfaces.poselection import *
from canonical.launchpad.interfaces.posubmission import *
from canonical.launchpad.interfaces.processor import *
from canonical.launchpad.interfaces.product import *
from canonical.launchpad.interfaces.productrelease import *
from canonical.launchpad.interfaces.productseries import *
from canonical.launchpad.interfaces.project import *
from canonical.launchpad.interfaces.publishedpackage import *
from canonical.launchpad.interfaces.publishing import *
from canonical.launchpad.interfaces.pyarch import *
from canonical.launchpad.interfaces.queue import *
from canonical.launchpad.interfaces.rawfiledata import *
from canonical.launchpad.interfaces.rosettastats import *
from canonical.launchpad.interfaces.schema import *
from canonical.launchpad.interfaces.section import *
from canonical.launchpad.interfaces.sourcepackage import *
from canonical.launchpad.interfaces.sourcepackageindistro import *
from canonical.launchpad.interfaces.sourcepackagename import *
from canonical.launchpad.interfaces.sourcepackagerelease import *
from canonical.launchpad.interfaces.spokenin import *
from canonical.launchpad.interfaces.ssh import *
from canonical.launchpad.interfaces.translationgroup import *
from canonical.launchpad.interfaces.translator import *
from canonical.launchpad.interfaces.vpoexport import *
from canonical.launchpad.interfaces.vsourcepackagereleasepublishing import *
from canonical.launchpad.interfaces.wikiname import *
from canonical.launchpad.interfaces.poexportrequest import *

from canonical.launchpad.interfaces.cal import *

# XXX sabdfl 29/03/05 given the comments at the top of the file, should
# these not be elsewhere?

class IAuthApplication(Interface):
    """ Interface for AuthApplication """
    def __getitem__(name):
        """ The __getitem__ method used to traversing """

    def sendPasswordChangeEmail(longurlsegment, toaddress):
        """Send an Password change special link for a user."""

    def getPersonFromDatabase(emailaddr):
        """Returns the Person in the database who has the given email address.

        If there is no Person for that email address, returns None.
        """

    def newLongURL(person):
        """Creates a new long url for the given person.

        Returns the long url segment.
        """

class IPasswordResets(IPersistent):
    """Interface for PasswordResets"""

    lifetime = Attribute("Maximum time between request and reset password")
    
    def newURL(person):
        """Create a new URL and store person and creation time"""
        
        
    def getPerson(long_url):
        """Get the person object using the long_url if not expired"""

class IPasswordChangeApp(Interface):
    """Interface for PasswdChangeApp."""
    code = Attribute("The transaction code")

