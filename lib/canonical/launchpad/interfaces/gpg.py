# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# GPG Interfaces
#

class IGPGKey(Interface):
    """GPG support"""
    person = Attribute("Owner")
    keyid = Attribute("KeyID")
    pubkey = Attribute("Pub Key itself")
    fingerprint = Attribute("User Fingerprint")
    revoked = Attribute("Revoked")
    algorithm = Attribute("Algorithm")
    keysize = Attribute("Keysize")
    algorithmname = Attribute("Algorithm Name")
    
