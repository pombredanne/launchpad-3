# (c) Canonical Software Ltd. 2004, all rights reserved.
#

# Lucille's primary interface to the upload mechanism

import logging
import shutil
import os
import stat
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
        lockfile_path = os.path.join(self.targetpath, ".lock")
        self.lock = GlobalLock(lockfile_path)
        # XXX cprov 20071024: We try to acquire the lock as soon as possible
        # after creating the lockfile but are still open to a race.
        # See bug #156795.
        self.lock.acquire(blocking=True)

        # Adjust lockfile permissions to allow the runner of process-upload
        # (lp_queue, member of lp_upload group) to be blocked on it (g+w).
        mode = stat.S_IMODE(os.stat(lockfile_path).st_mode)
        os.chmod(lockfile_path, mode | stat.S_IWGRP)

        try:
            self.targetcount += 1
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            path = "upload-%s-%06d" % (timestamp, self.targetcount)
            target_fsroot = os.path.join(self.targetpath, path)

            # Create file to store the distro used.
            self.logger.debug("Upload was targetted at %s" % client["distro"])
            distro_filename = target_fsroot + ".distro"
            distro_file = open(distro_filename, "w")
            distro_file.write(client["distro"])
            distro_file.close()

            # Move the session directory to the target directory.
            if os.path.exists(target_fsroot):
                self.logger.warn("Targeted upload already present: %s" % path)
                self.logger.warn("System clock skewed ?")
            else:
                try:
                    shutil.move(fsroot, target_fsroot)
                except (OSError, IOError):
                    if not os.path.exists(target_fsroot):
                        raise

            # XXX cprov 20071024: We should replace os.system call by os.chmod
            # and fix the default permission value accordingly in poppy-upload
            if self.perms is not None:
                os.system("chmod %s %s" % (self.perms, target_fsroot))

            # Invoke processing script, if provided.
            if self.cmd:
                cmd = self.cmd
                cmd = cmd.replace("@fsroot@", target_fsroot)
                cmd = cmd.replace("@distro@", client["distro"])
                self.logger.debug("Running upload handler: %s" % cmd)
                os.system(cmd)
        finally:
            # We never delete the lockfile, this way the inode will be
            # constant while the machine is up. See comment on 'acquire'
            self.lock.release(skip_delete=True)

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
