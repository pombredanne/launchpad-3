# (c) Canonical Software Ltd. 2004, all rights reserved.
#

# Lucille's primary interface to the upload mechanism

import logging
import shutil
import os
import time

from canonical.lp import initZopeless
from contrib.glock import GlobalLock

class PoppyInterfaceFailure(Exception):
    pass

class PoppyInterface:

    clients = {}

    def __init__(self, targetpath, logger, allow_user, cmd=None,
                 targetstart=0, perms=None):
        self.tm = initZopeless(dbuser='ro')
        self.targetpath = targetpath
        self.logger = logging.getLogger("%s.PoppyInterface" % logger.name)
        self.cmd = cmd
        self.allow_user = allow_user
        self.targetcount = targetstart
        self.perms = perms
        self.lock = GlobalLock(os.path.join(self.targetpath, ".lock"))

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
            raise PoppyInterfaceFailure("Unable to find fsroot in client set")

        self.logger.debug("Processing session complete in %s" % fsroot)

        client = self.clients[fsroot]
        if "distro" not in client:
            # Login username defines the distribution context of the upload.
            # So abort unauthenticated sessions by removing its contents
            shutil.rmtree(fsroot)
            return

        # Protect from race condition between creating the directory
        # and creating the distro file, and also in cases where the
        # temporary directory and the upload directory are not in the
        # same filesystem (non-atomic "rename").
        self.lock.acquire(blocking=True)

        # Move it to the target directory.
        while True:
            self.targetcount += 1
            target_fsroot = os.path.join(self.targetpath,
                                         "upload-%s-%06d" % (
                time.strftime("%Y%m%d-%H%M%S"), self.targetcount))
            if not os.path.exists(target_fsroot):
                try:
                    shutil.move(fsroot, target_fsroot)
                except (OSError, IOError):
                    if not os.path.exists(target_fsroot):
                        raise
                    continue
                break

        # Create file to store the distro used.
        self.logger.debug("Upload was targetted at %s" % client["distro"])
        distro_filename = target_fsroot + ".distro"
        distro_file = open(distro_filename, "w")
        distro_file.write(client["distro"])
        distro_file.close()

        if self.perms is not None:
            os.system("chmod %s %s" % (self.perms, target_fsroot))

        # We need to skip deletion here because we renamed the
        # directory, and therefore GlobalLock no longer knows where the
        # lockfile actually is.
        self.lock.release(skip_delete=True)

        # Invoke processing script, if provided.
        if self.cmd:
            cmd = self.cmd
            cmd = cmd.replace("@fsroot@", target_fsroot)
            cmd = cmd.replace("@distro@", client["distro"])
            self.logger.debug("Running upload handler: %s" % cmd)
            os.system(cmd)

        self.clients.pop(fsroot)

    def auth_verify_hook(self, fsroot, user, password):
        """Verify that the username matches a distribution we care about.

        The password is irrelevant to auth, as is the fsroot"""
        if fsroot not in self.clients:
            raise PoppyInterfaceFailure("Unable to find fsroot in client set")

        # local authentication
        self.clients[fsroot]["distro"] = self.allow_user
        return True

        # When we get on with the poppy path stuff, the below may be useful and
        # is thus left in rather than being removed.

        #try:
        #    d = Distribution.byName(user)
        #    if d:
        #        self.logger.debug("Accepting login for %s" % user)
        #        self.clients[fsroot]["distro"] = user
        #        return True
        #except object, e:
        #    print e
        #return False
