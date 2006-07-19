#!/usr/bin/env python
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath

import os
import sys
import time
import fcntl
import errno

from optparse import OptionParser
from email import message_from_string

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)
from canonical.launchpad.mail import sendmail
from canonical.encoding import ascii_smash

from contrib.glock import GlobalLock

from canonical.archivepublisher.nascentupload import NascentUpload, UploadError
from canonical.archivepublisher.uploadpolicy import (
    findPolicyByOptions, policy_options, UploadPolicyError)

from zope.component import getUtility
from canonical.launchpad.interfaces import IGPGHandler


# Globals set in main()
log = None
options = None


def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)
    policy_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help=("Whether to treat this as a dry-run or not. "
                            "Implicitly set -KM."))

    parser.add_option("-K", "--keep", action="store_true",
                      dest="keep", metavar="KEEP", default=False,
                      help="Whether to keep or not the uploads directory.")

    parser.add_option("-M", "--no-mails", action="store_true",
                      dest="nomails", default=False,
                      help="Whether to suppress the sending of mails or not.")

    parser.add_option("-L", "--loop", action="store_true", default=False,
                      help="Wait for more uploads rather than exiting.")

    parser.add_option("-J", "--just-leaf", action="store", dest="leafname",
                      default=None, help="A specific leaf dir to limit to.",
                      metavar = "LEAF")

    global options
    (options, args) = parser.parse_args()

    global log
    log = logger(options, "process-upload")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the fsroot for the upload.")
        return 1

    base_fsroot = os.path.abspath(args[0])
    if not os.path.isdir(base_fsroot):
        raise ValueError("%s is not a directory" % base_fsroot)
    options.base_fsroot = base_fsroot

    for subdir in ["incoming", "accepted", "rejected", "failed"]:
        full_subdir = os.path.join(base_fsroot, subdir)
        if not os.path.exists(full_subdir):
            log.debug("Creating directory %s" % full_subdir)
            os.mkdir(full_subdir)

    fsroot = os.path.join(base_fsroot, "incoming")

    lock = GlobalLock('/var/lock/launchpad-upload-queue.lock')

    log.debug("Initialising connection.")
    ztm = initZopeless(dbuser=config.uploader.dbuser)

    execute_zcml_for_scripts()

    try:

        # This is going to process the list of directories in the
        # given root. For each directory, it tries to acquire an
        # exclusive lock. If successfully acquired, uploads in that
        # directory are processed. If the lock is already taken,
        # it means someone else is already handling it and we don't
        # have to bother.

        # XXX [1] Daniel, can we run process_upload() in parallel or is
        # it really not safe?  I'm keeping the lock around it, since I
        # belive you know about a race condition that would be the reason
        # why you were originally locking the whole main function (haven't
        # investigated the code).  If the lock is really meaningful,
        # there's no reason why we should run two process-upload.py
        # instances in parallel, and consequently the fine grained
        # locking below is not useful, and neither is poppy-upload
        # spawning multiple process-upload.py in parallel, IMO.
        #
        # See [2] for the current locking place. Bug 29694 covers this
        # issue.
        #
        # -- Gustavo Niemeyer, 2005-12-19

        fsroot_lock = GlobalLock(os.path.join(fsroot, ".lock"))

        while True:

            # Protecting listdir by a lock ensures that we only get
            # completely finished directories listed. See
            # PoppyInterface for the other locking place.
            fsroot_lock.acquire()
            entries = os.listdir(fsroot)
            fsroot_lock.release()

            for entry in entries:
                if options.leafname is not None:
                    if entry != options.leafname:
                        log.debug("Skipping %s -- does not match %s" % (
                            entry, options.leafname))
                        continue
                do_one_entry(ztm, entry, fsroot, lock)

            if not options.loop:
                break

            # Sleep 5 seconds before scanning the whole root
            # directory again (that's NOT for each upload).
            # XXX: untested
            time.sleep(5)


    finally:
        log.debug("Rolling back any remaining transactions.")
        ztm.abort()

    return 0


def send_mails(mails):
    """Send the mails provided using the launchpad mail infrastructure."""
    for mail_text in mails:
        mail_message = message_from_string(ascii_smash(mail_text))
        if mail_message['To'] is None:
            log.debug("Unable to parse message for rejection!")
            log.debug("This will cause the sendmail() to assert.")
            print repr(mail_text)
        mail_message['X-Katie'] = "Launchpad actually"
        if options.dryrun or options.nomails:
            log.info("Would be sending a mail:")
            log.info("   Subject: %s" % mail_message['Subject'])
            log.info("   Recipients: %s" % mail_message['To'])
            log.info("   Body:")
            for line in mail_message.get_payload().split("\n"):
                log.info(line)
        else:
            sendmail(mail_message)


def process_upload(ztm, upload, entry_path):
    """Process an upload as provided."""
    ztm.begin()
    log.info("Processing upload %s" % upload.changes_filename)
    destination = None

    try:
        try:
            upload.process()
        except UploadPolicyError, e:
            upload.reject("UploadPolicyError made it out to the main loop: "
                          "%s " % e)
            log.debug("UploadPolicyError made it out of .process()",
                      exc_info=True)
            destination = "failed"
        except UploadError, e:
            upload.reject("UploadError made it out to the main loop: %s" % e)
            log.debug("UploadError made it out of .process()", exc_info=True)
            destination = "failed"
        if upload.rejected:
            mails = upload.do_reject()
            ztm.abort()
            send_mails(mails)
            if destination is None:
                destination = "rejected"
        else:
            successful, mails = upload.do_accept()
            if successful:
                destination = "accepted"
            else:
                log.info("Rejection during accept. Aborting partial accept.")
                ztm.abort()
                destination = "rejected"
            send_mails(mails)
        if options.dryrun:
            log.info("Dry run, aborting the transaction for this upload.")
            ztm.abort()
        else:
            log.info("Committing the transaction and any mails associated "
                     "with this upload.")
            ztm.commit()

        log.info("Cleaning out the GPG handlers")
        getUtility(IGPGHandler).resetLocalState()
    except:
        log.warn("Exception during processing made it out of the main loop.",
                 exc_info=True)
        destination = "failed"


    ztm.abort()

    if destination is None:
        destination = "failed"

    return destination

def move_subdirectory(entry_path, subdir):
    if options.keep or options.dryrun:
        log.debug("Keeping contents untouched")
        return

    pathname = os.path.basename(entry_path)

    target_path = os.path.join(options.base_fsroot, subdir, pathname)
    log.debug("Moving upload directory %s to %s" % (entry_path,
                                                    target_path))
    os.rename(entry_path, target_path)

    distro_filename = entry_path + ".distro"
    if os.path.isfile(distro_filename):
        target_path = os.path.join(options.base_fsroot, subdir,
                                   os.path.basename(distro_filename))
        log.debug("Moving distro file %s to %s" % (distro_filename,
                                                   target_path))
        os.rename(distro_filename, target_path)


def compare_filenames(a, b):
    """Compare filenames a and b for ordering.

    In particular, _source.changes sorts earlier than non source.
    Otherwise it's a string compare.
    """
    a_sourceful = a.endswith("_source.changes")
    b_sourceful = b.endswith("_source.changes")
    if a_sourceful and not b_sourceful:
        return -1
    if b_sourceful and not a_sourceful:
        return 1
    # Compare by filename
    return cmp(a,b)


def order_filenames(fnames):
    """Order filenames by upload type and then filenamename."""
    fnames = list(fnames)
    fnames.sort(cmp=compare_filenames)
    return fnames


def do_one_entry(ztm, entry, fsroot, lock):
    entry_path = os.path.join(fsroot, entry)
    if not os.path.isdir(entry_path):
        return

    try:
        log.debug("Trying to lock upload directory: %s" %
                  entry_path)
        entry_fd = os.open(entry_path, os.O_RDONLY)
        # This lock would be useful if/when we remove the
        # global lock above -- it would return an
        # errno.EAGAIN if anyone is already touching that
        # directory.
        fcntl.flock(entry_fd, fcntl.LOCK_EX|fcntl.LOCK_NB)

    except IOError, e:
        if e.errno != errno.EAGAIN:
            raise
        log.debug("Upload directory is already locked")

    else:
        log.debug("Got the upload directory lock")

        uploads = []

        # We override the distro option with information
        # provided in the FTP session, if available.
        distro_filename = entry_path + ".distro"
        options_distro = options.distro
        if os.path.isfile(distro_filename):
            distro_file = open(distro_filename)
            options.distro = distro_file.read()
            distro_file.close()
            log.debug("Overriding distribution: %s" %
                      options.distro)


        for filename in order_filenames(os.listdir(entry_path)):
            if filename.endswith(".changes"):
                log.debug("Finding fresh policy")
                policy = findPolicyByOptions(options)
                uploads.append(NascentUpload(
                    policy, entry_path, filename, log))

        destination = None

        for upload in uploads:
            # XXX [2] Do we really need this lock? See [1].
            log.debug("Acquiring process_upload lock")
            lock.acquire(blocking=True)
            try:
                destination = process_upload(ztm, upload, entry_path)
            finally:
                log.debug("Releasing process_upload lock")
                lock.release()

        if destination is None:
            destination = "failed"

        move_subdirectory(entry_path, destination)

        options.distro = options_distro

        # Unlock it and release the removed directory by
        # closing the file descriptor.
        os.close(entry_fd)


if __name__ == '__main__':
    sys.exit(main())


