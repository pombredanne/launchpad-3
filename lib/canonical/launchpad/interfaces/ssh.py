from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

__all__ = ['ISSHKey']

class ISSHKey(Interface):
    """SSH public key"""
    id = Attribute(_("ID"))
    person = Attribute(_("Owner"))
    keytype = Attribute(_("Key type (see canonical.lp.dbschema.SSHKeyType"))
    keytext = Attribute(_("Key text"))
    comment = Attribute(_("Comment describing this key"))

