#!/usr/bin/env python
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath

import os
import sys

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
    global options
    (options, args) = parser.parse_args()

    global log
    log = logger(options, "process-upload")

    if len(args) != 1:
        log.error("Need to be given exactly one non-option argument. "
                  "Namely the fsroot for the upload.")
        return 1

    fsroot = args[0]

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-process-upload.lock')
    lock.acquire(blocking=True)

    log.debug("Initialising connection.")
    global ztm
    ztm = initZopeless(dbuser=config.uploader.dbuser)

    execute_zcml_for_scripts()

    try:
        if not os.path.isdir(fsroot):
            raise ValueError("%s is not a directory" % fsroot)
        log.info("Finding policy.")
        policy = findPolicyByOptions(options)

        uploads = []

        for root, dirs, files in os.walk(fsroot):
            assert(len(dirs) == 0)
            for filename in files:
                if filename.endswith(".changes"):
                    uploads.append(
                        NascentUpload(policy, fsroot, filename, log))

        for upload in uploads:
            process_upload(upload)

    finally:
        log.debug("Rolling back any remaining transactions.")
        ztm.abort()
        log.debug("Releasing lock")
        lock.release()

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
        if options.dryrun:
            log.info("Would be sending a mail:")
            log.info("   Subject: %s" % mail_message['Subject'])
            log.info("   Recipients: %s" % mail_message['To'])
            log.info("   Body:")
            for line in mail_message.get_payload().split("\n"):
                log.info(line)
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
            mails = upload.do_accept()
            send_mails(mails)
        if options.dryrun:
            log.info("Dry run, aborting the transaction for this upload.")
            ztm.abort()
        else:
            log.info("Committing the transaction for this upload.")
            ztm.commit()
    finally:
        ztm.abort()

if __name__ == '__main__':
    sys.exit(main())

