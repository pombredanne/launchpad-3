from twisted.conch import avatar
from twisted.conch.ssh import session, filetransfer
#from twisted.conch.interfaces import ISession


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        if name.startswith('request') and name != 'request_subsystem':
            raise AttributeError, name
        return object.__getattribute__(self, name)

    #def request_shell(self, data):
    #    return False
    #def request_exec(self, data):
    #    return False
    #def request_pty_req(self, data):
    #    return False
    #def request_window_change(self, data):
    #    return False


class SFTPOnlyAvatar(avatar.ConchUser):
    # Set the only channel as a session that only allows requests for
    # subsystems...
    channelLookup = {'session': SubsystemOnlySession}
    # ...and set the only subsystem to be SFTP.
    subsystemLookup = {'sftp': filetransfer.FileTransferServer}


#class SFTPOnlySessionAdapter:
#    implements(ISession)
#
#    def __init__(self, avatar):
#        """
#        We don't use it, but the adapter is passed the avatar as its first
#        argument.
#        """
#
#    def getPty(self, term, windowSize, attrs):
#        """Disabled."""
#        pass
#    
#    def execCommand(self, proto, cmd):
#        """Disabled"""
#        # XXX: Is there a better way to do this?
#        raise Exception("no executing commands")
#
#    def openShell(self, trans):
#        """Disabled"""
#        # XXX: Is there a better way to do this?
#        raise Exception("no executing commands")
#
#    def windowChanged(self, newWindowSize):
#        """Disabled"""
#        pass
#
#    def eofReceived(self):
#        # XXX: Do we need to do anything here?
#        pass
#
#    def closed(self):
#        # XXX: Do we need to do anything here?
#        pass
#        
#
#
#from twisted.python import components
#components.registerAdapter(SFTPOnlySessionAdapter, SFTPOnlyAvatar, ISession)

