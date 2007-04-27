# Copyright 2006 Canonical Ltd.  All rights reserved.
#

"""Code for 'processing' 'uploads'. Also see nascentupload.py.

Uploads are directories in the 'incoming' queue directory. They may have
arrived manually from a distribution contributor, via a poppy upload, or
they may have come from a build.

Within an upload, we may find no changes file, one, or several. One is
the usual number. To process the upload, we process each changes file
in turn.

To process a changes file, we make checks such as that the other files
referenced by it are present, formatting is valid, signatures are correct,
checksums match, and that the .changes file represents an upload which makes
sense, eg. it is not a binary for which we have no source, or an older
version than already exists in the same target distrorelease pocket.

Depending on the outcome of these checks, the changes file will either be
accepted (and the information from it, and the referenced files, imported
into the database) or it won't (and the database will be unchanged). If not
accepted, a changes file might be 'failed' or 'rejected', where failed
changes files are dropped silently, but rejected ones generate a rejection
email back to the uploader.

There are several valid reasons to fail (the changes file is so mangled
that we can't read who we should send a rejection to, or it's not correctly
signed, so we can't be sure a rejection wouldn't be spam (it may not have
been uploaded by who it says it was uploaded by). In practice, in the code
as it stands, we also consider the processing of a changes file to have
failed if it generates an unexpected exception, and there are some known
cases where it does this and a rejection would have been more useful
(see bug 35965).

Each upload directory is saved after processing, in case it is needed for
debugging purposes. This is done by moving it to a directory inside the queue
directory, beside incoming, named after the result - 'failed', 'rejected' or
'accepted'. Where there are no changes files, the upload is considered failed,
and where there is more than one changes file, the upload is assigned the
worst of the results from the various changes files found (in the order
above, failed being worst).

"""

__metaclass__ = type

from email import message_from_string
import os
import shutil

from canonical.launchpad.mail import sendmail
from canonical.encoding import ascii_smash
from canonical.archivepublisher.nascentupload import (
    NascentUpload, FatalUploadError)
from canonical.archivepublisher.uploadpolicy import (
    findPolicyByOptions, UploadPolicyError)

from contrib.glock import GlobalLock

__all__ = ['UploadProcessor']


class UploadStatusEnum:
    """Possible results from processing an upload.

    ACCEPTED: all goes well, we commit nascentupload's changes to the db
    REJECTED: nascentupload gives a well-formed rejection error,
              we send a rejection email and rollback.
    FAILED: nascentupload code raises an exception, no email, rollback
    """
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    FAILED = 'failed'


class UploadProcessor:
    """Responsible for processing uploads. See module docstring."""

    def __init__(self, options, ztm, log):
        self.options = options
        self.ztm = ztm
        self.log = log
        self.processed_uploads = None

    def processUploadQueue(self):
        """Search for uploads, and process them.

	Uploads are searched for in the 'incoming' directory inside the
        base_fsroot.

        This method also creates the 'incoming', 'accepted', 'rejected', and
        'failed' directories inside the base_fsroot if they don't yet exist.
        """
        try:
            self.log.debug("Beginning processing")

            for subdir in ["incoming", "accepted", "rejected", "failed"]:
                full_subdir = os.path.join(self.options.base_fsroot, subdir)
                if not os.path.exists(full_subdir):
                    self.log.debug("Creating directory %s" % full_subdir)
                    os.mkdir(full_subdir)

            fsroot = os.path.join(self.options.base_fsroot, "incoming")
            uploads_to_process = self.locateDirectories(fsroot)
            self.log.debug("Checked in %s, found %s"
                           % (fsroot, uploads_to_process))
            for upload in uploads_to_process:
                self.log.debug("Considering upload %s" % upload)
                self.processUpload(fsroot, upload)

        finally:
            self.log.debug("Rolling back any remaining transactions.")
            self.ztm.abort()

    def processUpload(self, fsroot, upload):
        """Process an upload's changes files, and move it to a new directory.

        The destination directory depends on the result of the processing
        of the changes files. If there are no changes files, the result
        is 'failed', otherwise it is the worst of the results from the
        individual changes files, in order 'failed', 'rejected', 'accepted'.

        If the leafname option is set but its value is not the same as the
        name of the upload directory, skip it entirely.

        """
        if (self.options.leafname is not None and
            upload != self.options.leafname):
            self.log.debug("Skipping %s -- does not match %s" % (
                upload, self.options.leafname))
            return

        upload_path = os.path.join(fsroot, upload)
        changes_files = self.locateChangesFiles(upload_path)

        # Keep track of the various results
        some_failed = False
        some_rejected = False
        some_accepted = False

        for changes_file in changes_files:
            self.log.debug("Considering changefile %s" % changes_file)
            try:
                result = self.processChangesFile(upload_path, changes_file)
                if result == UploadStatusEnum.FAILED:
                    some_failed = True
                elif result == UploadStatusEnum.REJECTED:
                    some_rejected = True
                else:
                    some_accepted = True
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.log.error("Unhandled exception from processing an upload",
                               exc_info=True)
                some_failed = True

        if some_failed:
            destination = "failed"
        elif some_rejected:
            destination = "rejected"
        elif some_accepted:
            destination = "accepted"
        else:
            # There were no changes files at all. We consider
            # the upload to be failed in this case.
            destination = "failed"

        self.moveUpload(upload_path, destination)

    def locateDirectories(self, fsroot):
        """List directories in given directory, usually 'incoming'."""
        # Protecting listdir by a lock ensures that we only get
        # completely finished directories listed. See
        # PoppyInterface for the other locking place.
        fsroot_lock = GlobalLock(os.path.join(fsroot, ".lock"))
        try:
            fsroot_lock.acquire(blocking=True)
            dir_names = os.listdir(fsroot)
        finally:
            fsroot_lock.release()

        dir_names = [dir_name for dir_name in dir_names if
                     os.path.isdir(os.path.join(fsroot, dir_name))]
        return dir_names

    def locateChangesFiles(self, upload_path):
        """Locate .changes files in the given upload directory.

        Return .changes files sorted with *_source.changes first.
        """
        changes_files = []
        for filename in self.orderFilenames(os.listdir(upload_path)):
            if filename.endswith(".changes"):
                changes_files.append(filename)
        return changes_files

    def processChangesFile(self, upload_path, changes_file):
        """Process a single changes file.

        This is done by obtaining the appropriate upload policy (according
        to command-line options and the value in the .distro file beside
        the upload, if present), creating a NascentUpload object and calling
        its process method.

        See nascentupload.py for the gory details.

        Returns a value from UploadStatusEnum, or re-raises an exception
        from NascentUpload.
        """
        # Cache original value of self.options.distro, from command-line
        options_distro = self.options.distro

        # Override self.options.distro from .distro file, if present
        distro_filename = upload_path + ".distro"
        if os.path.isfile(distro_filename):
            distro_file = open(distro_filename)
            self.options.distro = distro_file.read()
            distro_file.close()
            self.log.debug("Overriding distribution: %s" %
                           self.options.distro)

        # Get the policy, using the overriden options
        self.log.debug("Finding fresh policy")
        policy = findPolicyByOptions(self.options)

        # Restore original value for self.options.distro
        self.options.distro = options_distro

        changesfile_path = os.path.join(upload_path, changes_file)
        upload = NascentUpload(changesfile_path, policy, self.log)

        # Store processed NascentUpload instance, mostly used for tests.
        self.last_processed_upload = upload

        try:
            self.log.info("Processing upload %s" % upload.changes.filename)
            result = UploadStatusEnum.ACCEPTED

            try:
                upload.process()
            except UploadPolicyError, e:
                upload.reject("UploadPolicyError escaped upload.process: "
                              "%s " % e)
                self.log.debug("UploadPolicyError escaped upload.process",
                               exc_info=True)
            except FatalUploadError, e:
                upload.reject("UploadError escaped upload.process: %s" % e)
                self.log.debug("UploadError escaped upload.process",
                               exc_info=True)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                # In case of unexpected unhandled exception, we'll
                # *try* to reject the upload. This may fail and cause
                # a further exception, depending on the state of the
                # nascentupload objects. In that case, we've lost nothing,
                # the new exception will be handled by the caller just like
                # the one we caught would have been, by failing the upload
                # with no email.
                self.log.exception("Unhandled exception processing upload")
                upload.reject("Unhandled exception processing upload: %s" % e)

            if upload.is_rejected:
                result = UploadStatusEnum.REJECTED
                mails = upload.do_reject()
                self.ztm.abort()
                self.sendMails(mails)
            else:
                successful, mails = upload.do_accept()
                if not successful:
                    result = UploadStatusEnum.REJECTED
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

        return result

    def moveUpload(self, upload, subdir_name):
        """Move the upload to the named subdir of the root, eg 'accepted'.

        This includes moving the given upload directory and moving the
        matching .distro file, if it exists.
        """
        if self.options.keep or self.options.dryrun:
            self.log.debug("Keeping contents untouched")
            return

        pathname = os.path.basename(upload)

        target_path = os.path.join(
            self.options.base_fsroot, subdir_name, pathname)
        self.log.debug("Moving upload directory %s to %s" %
            (upload, target_path))
        shutil.move(upload, target_path)

        distro_filename = upload + ".distro"
        if os.path.isfile(distro_filename):
            target_path = os.path.join(self.options.base_fsroot, subdir_name,
                                       os.path.basename(distro_filename))
            self.log.debug("Moving distro file %s to %s" % (distro_filename,
                                                            target_path))
            shutil.move(distro_filename, target_path)

    def sendMails(self, mails):
        """Send the mails provided using the launchpad mail infrastructure."""
        for mail_text in mails:
            mail_message = message_from_string(ascii_smash(mail_text))

            if mail_message['To'] is None:
                self.log.debug("Missing recipient: empty 'To' header")
                print repr(mail_text)
                continue

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
            for line in mail_message.get_payload().splitlines():
                logger(line)

    def orderFilenames(self, fnames):
        """Order filenames, sorting *_source.changes before others.

        Aside from that, a standard string sort.
        """
        def sourceFirst(filename):
            return (not filename.endswith("_source.changes"), filename)

        return sorted(fnames, key=sourceFirst)

