# (c) Canonical Software Ltd. 2004, all rights reserved.
#

# Lucille's primary interface to the upload mechanism

from canonical.lp import initZopeless
from canonical.launchpad.database import Distribution
import logging
import shutil
from os import system

class PoppyInterfaceFailure(Exception):
    pass

class PoppyInterface:

    clients = {}

    def __init__(self, logger, cmd=None, background=True):
        self.tm = initZopeless()
        self.logger = logging.getLogger("%s.PoppyInterface" % logger.name)

        if cmd is None:
            self.cmd = ['echo', '@distro@', ';', 'ls', '@fsroot@']
        else:
            self.cmd = cmd

        self.background = background
        
    def new_client_hook(self, fsroot, host, port):
        """Prepare a new client record indexed by fsroot..."""
        self.clients[fsroot] = {
            "host": host,
            "port": port
            }
        self.logger.debug("Accepting new session in fsroot: %s" % fsroot);
        self.logger.debug("Session from %s:%s" % (host,port))

    def client_done_hook(self, fsroot, host, port):
        """A client has completed. If it authenticated then it stands a chance
        of having uploaded a file to the set. If not; then it is simply an
        aborted transaction and we remove the fsroot."""
        if fsroot not in self.clients:
            raise PoppyInterfaceFailure, "Unable to find fsroot in client set"
        self.logger.debug("Processing session complete in %s" % fsroot)
        c = self.clients[fsroot]
        if "distro" not in c:
            # Nope, not an authenticated client; abort
            shutil.rmtree(fsroot)
            return
        # Was an authenticated client; so we leave the fsroot in place
        # And invoke our processing script...
        self.logger.debug("Upload was targetted at %s" % c["distro"])
        cmd = []
        for element in self.cmd:
            if element == "@fsroot@":
                cmd.append(fsroot)
            elif element == "@distro@":
                cmd.append(c["distro"])
            else:
                cmd.append(element)
        self.logger.debug("Running upload handler: %s" % (" ".join(cmd)))
        if self.background:
            cmd.append("&")
        system(" ".join(cmd))
        self.clients.pop(fsroot)

    def auth_verify_hook(self, fsroot, user, password):
        """Verify that the username matches a distribution we care about.

        The password is irrelevant to auth, as is the fsroot"""
        if fsroot not in self.clients:
            raise PoppyInterfaceFailure, "Unable to find fsroot in client set"
        try:
            d = Distribution.byName(user)
            if d:
                self.logger.debug("Accepting login for %s" % user)
                self.clients[fsroot]["distro"] = user
                return True
        except object, e:
            print e
        return False


