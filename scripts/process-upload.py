#!/usr/bin/env python
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath

import os
import sys
import fcntl
import shutil

from optparse import OptionParser
from email import message_from_string

from zope.component import getUtility

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

def main():
    # Parse command-line arguments
    parser = OptionParser()
    logger_options(parser)
    policy_options(parser)

    parser.add_option("-N", "--dry-run", action="store_true",
                      dest="dryrun", metavar="DRY_RUN", default=False,
                      help="Whether to treat this as a dry-run or not.")

    parser.add_option("-M", "--no-mails", action="store_true",
                      dest="nomails", default=False,
                      help="Whether to suppress the sending of mails or not.")

    parser.add_option("-l", "--loop", action="store_true", default=False,
                      help="Wait for more uploads rather than exiting.")
    
    global options
    (options, args) = parser.parse_args()

    global log
    log = logger(options, "process-upload")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the fsroot for the upload.")
        return 1

    fsroot = os.path.abspath(args[0])
    if not os.path.isdir(fsroot):
        raise ValueError("%s is not a directory" % fsroot)

    lock = GlobalLock('/var/lock/launchpad-process-upload.lock')

    log.debug("Initialising connection.")
    global ztm
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
        # See [2] for the current locking place.
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
                
                entry_path = os.path.join(fsroot, entry)
                if not os.path.isdir(entry_path):
                    continue

                try:
                    log.debug("Trying to lock upload directory: %s" %
                              entry_path)
                    entry_fd = os.open(entry_path, os.O_RDONLY)
                    fcntl.flock(entry_fd, fcntl.LOCK_EX|fcntl.LOCK_NB)

                except IOError, e:
                    log.debug("Upload directory is already locked")
                    if e.errno != 11:
                        raise

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

                    log.debug("Finding policy")
                    policy = findPolicyByOptions(options)

                    for filename in os.listdir(entry_path):
                        if filename.endswith(".changes"):
                            uploads.append(NascentUpload(
                                policy, entry_path, filename, log))

                    for upload in uploads:
                        # XXX [2] Do we really need this lock? See [1].
                        log.debug("Acquiring process_upload lock")
                        lock.acquire(blocking=True)
                        try:
                            process_upload(upload)
                        finally:
                            log.debug("Releasing process_upload lock")
                            lock.release()

                    log.debug("Removing upload directory: %s" % entry_path)
                    shutil.rmtree(entry_path)

                    if os.path.isfile(distro_filename):
                        log.debug("Removing distro file: %s" % distro_filename)
                        os.unlink(distro_filename)

                    options.distro = options_distro

                    # Unlock it and release the removed directory by
                    # closing the file descriptor.
                    os.close(entry_fd)

            if not options.loop:
                break

            # Sleep 5 seconds before scanning the whole root
            # directory again (that's NOT for each upload).
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
        
def process_upload(upload):
    """Process an upload as provided."""
    ztm.begin()
    log.info("Processing upload %s" % upload.changes_filename)
    try:
        try:
            upload.process()
        except UploadPolicyError, e:
            upload.reject("UploadPolicyError made it out to the main loop: "
                          "%s " % e)
        except UploadError, e:
            upload.reject("UploadError made it out to the main loop: %s" % e)
        if upload.rejected:
            mails = upload.do_reject()
            ztm.abort()
            send_mails(mails)
        else:
            successful, mails = upload.do_accept()
            if not successful:
                log.info("Rejection during accept. Aborting partial accept.")
                ztm.abort()
            send_mails(mails)
        if options.dryrun:
            log.info("Dry run, aborting the transaction for this upload.")
            ztm.abort()
        else:
            log.info("Committing the transaction and any mails associated "
                     "with this upload.")
            ztm.commit()
    finally:
        ztm.abort()

if __name__ == '__main__':
    sys.exit(main())
