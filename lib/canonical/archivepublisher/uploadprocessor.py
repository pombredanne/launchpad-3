import os
from email import message_from_string

from canonical.launchpad.mail import sendmail
from canonical.encoding import ascii_smash
from canonical.archivepublisher.nascentupload import (
    NascentUpload, UploadError)
from canonical.archivepublisher.uploadpolicy import (
    findPolicyByOptions, UploadPolicyError)

from contrib.glock import GlobalLock

__metaclass__ = type

__all__ = ['UploadProcessor']


class UploadProcessor:
    """Processes uploads"""
    
    def __init__(self, options, ztm, log):
        self.options = options
        self.ztm = ztm
        self.log = log

    def process(self):
        """Do some setup, loop over uploads and process each one."""
        try:
            self.log.debug("Beginning processing")
            
            for subdir in ["incoming", "accepted", "rejected", "failed"]:
                full_subdir = os.path.join(self.options.base_fsroot, subdir)
                if not os.path.exists(full_subdir):
                    self.log.debug("Creating directory %s" % full_subdir)
                    os.mkdir(full_subdir)

            fsroot = os.path.join(self.options.base_fsroot, "incoming")
            folders_to_process = self.locateFolders(fsroot)
            self.log.debug("Checked in %s, found %s"
                           % (fsroot, folders_to_process))
            for entry in folders_to_process:
                self.log.debug("Considering upload %s" % entry)
                self.processEntry(fsroot, entry)

        finally:
            self.log.debug("Rolling back any remaining transactions.")
            self.ztm.abort()
            
        return 0

    def processEntry(self, fsroot, entry):
        """Process (or skip) one upload directory."""
        if (self.options.leafname is not None and
            entry != self.options.leafname):
            self.log.debug("Skipping %s -- does not match %s" % (
                entry, self.options.leafname))
            return

        entry_path = os.path.join(fsroot, entry)        
        changes_files = self.locateChangesFiles(entry_path)

        # Keep track of the various results
        some_failed = False
        some_rejected = False
        some_accepted = False
        
        for changes_file in changes_files:
            self.log.debug("Considering changefile %s" % changes_file)
            try:
                (failed, rejected) = self.processChangesFile(entry_path,
                                                             changes_file)
                if failed:
                    some_failed = True
                elif rejected:
                    some_rejected = True
                else:
                    some_accepted = True

            # Copied this bare except from the previous script.
            # Not sure of the limits on the exceptions possible, so keeping
            # it. Re-raise KeyboardInterrupt, so at least that problem
            # of bare excepts goes away.
            except KeyboardInterrupt:
                raise
            except:
                self.log.debug("Unhandled exception from processing an upload",
                               exc_info=True)
                some_failed = True
                
        if some_failed:
            destination = "failed"
        elif some_rejected:
            destination = "rejected"
        elif some_accepted:
            destination = "accepted"
        else:
            destination = "failed"

        self.moveUpload(entry_path, destination)

    def locateFolders(self, fsroot):
        """List folders in given folder, usually the incoming folder."""
        # Protecting listdir by a lock ensures that we only get
        # completely finished directories listed. See
        # PoppyInterface for the other locking place.
        fsroot_lock = GlobalLock(os.path.join(fsroot, ".lock"))
        fsroot_lock.acquire()
        entries = os.listdir(fsroot)
        fsroot_lock.release()

        entries = [entry for entry in entries if
                   os.path.isdir(os.path.join(fsroot, entry))]
        return entries

    def locateChangesFiles(self, entry_path):
        """Locate .changes files in the given folder."""
        changes_files = []
        for filename in self.orderFilenames(os.listdir(entry_path)):
            if filename.endswith(".changes"):
                changes_files.append(filename)
        return changes_files
                
    def processChangesFile(self, entry_path, changes_file):
        """Process a single changes file.

        The change might be accepted, rejected or fail. The return
        value is a tuple of booleans, (failed, rejected). If both
        are false, the change was accepted.
        """
        # Cache default distro from command-line
        options_distro = self.options.distro

        # Override from .distro if present
        distro_filename = entry_path + ".distro"
        if os.path.isfile(distro_filename):
            distro_file = open(distro_filename)
            self.options.distro = distro_file.read()
            distro_file.close()
            self.log.debug("Overriding distribution: %s" %
                           self.options.distro)

        # Get the policy
        self.log.debug("Finding fresh policy")
        policy = findPolicyByOptions(self.options)

        # Restore default distro option
        self.options.distro = options_distro
        
        upload = NascentUpload(policy, entry_path, changes_file, self.log)

        try:
            self.ztm.begin()
            self.log.info("Processing upload %s" % upload.changes_filename)

            failed = False
            rejected = False

            try:
                upload.process()
            except UploadPolicyError, e:
                upload.reject("UploadPolicyError escaped upload.process: "
                              "%s " % e)
                self.log.debug("UploadPolicyError escaped upload.process",
                               exc_info=True)
                failed = True
            except UploadError, e:
                upload.reject("UploadError escaped upload.process: %s" % e)
                self.log.debug("UploadError escaped upload.process",
                               exc_info=True)
                failed = True
            if upload.rejected:
                rejected = True
                mails = upload.do_reject()
                self.ztm.abort()
                self.sendMails(mails)
            else:
                successful, mails = upload.do_accept()
                if not successful:
                    rejected = True
                    self.log.info("Rejection during accept. "
                                  "Aborting partial accept.")
                    self.ztm.abort()
                self.sendMails(mails)
                
            if self.options.dryrun:
                self.log.info("Dry run, aborting transaction.")
                self.ztm.abort()
            else:
                self.log.info("Committing the transaction and any mails "
                              "associated with this upload.")
                self.ztm.commit()
        except:
            self.ztm.abort()
            raise

        return (failed, rejected)
        

    def moveUpload(self, folder, subdir_name):
        """Move the upload to the named subdir of the root, eg 'accepted'.

        This includes moving the given folder and moving the matching
        .distro file, if it exists.
        """
        
        if self.options.keep or self.options.dryrun:
            self.log.debug("Keeping contents untouched")
            return

        pathname = os.path.basename(folder)

        target_path = os.path.join(
            self.options.base_fsroot, subdir_name, pathname)
        self.log.debug("Moving upload directory %s to %s" % (folder,
                                                        target_path))
        os.rename(folder, target_path)

        distro_filename = folder + ".distro"
        if os.path.isfile(distro_filename):
            target_path = os.path.join(self.options.base_fsroot, subdir_name,
                                       os.path.basename(distro_filename))
            self.log.debug("Moving distro file %s to %s" % (distro_filename,
                                                            target_path))
            os.rename(distro_filename, target_path)
                
    def sendMails(self, mails):
        """Send the mails provided using the launchpad mail infrastructure."""
        for mail_text in mails:
            mail_message = message_from_string(ascii_smash(mail_text))
            if mail_message['To'] is None:
                self.log.debug("Unable to parse message for rejection!")
                self.log.debug("This will cause the sendmail() to assert.")
                print repr(mail_text)
            mail_message['X-Katie'] = "Launchpad actually"

            logger = self.log.debug
            if self.options.dryrun or self.options.nomails:
                logger = self.log.info
                logger("Would be sending a mail:")
            else:
                sendmail(mail_message)
                logger("Sent a mail:")
                
            logger("   Subject: %s" % mail_message['Subject'])
            logger("   Recipients: %s" % mail_message['To'])
            logger("   Body:")
            for line in mail_message.get_payload().split("\n"):
                logger(line)

    def orderFilenames(self, fnames):
        """Order filenames, sorting *_source.changes before others.

        Aside from that, a standard string sort.
        """

        def compareFilenames(a, b):
            sourceful_prefix = "_source.changes"
            a_sourceful = a.endswith(sourceful_prefix)
            b_sourceful = b.endswith(sourceful_prefix)
            if a_sourceful and not b_sourceful:
                return -1
            if b_sourceful and not a_sourceful:
                return 1
            return cmp(a, b)

        fnames = list(fnames)
        fnames.sort(cmp=compareFilenames)
        return fnames
