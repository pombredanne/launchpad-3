#!/usr/bin/env python
"""Upload test.

"""
import subprocess
import tempfile
import optparse
import logging
import ftplib
import shutil
import urllib
import rfc822
import sys
import os
import time

import _pythonpath

from zope.component import getUtility

from contrib.glock import GlobalLock

from sqlobject.main import SQLObjectIntegrityError

from canonical.lp import initZopeless
from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)

from canonical.launchpad.utilities.gpghandler import PymeKey

from canonical.launchpad.interfaces import (
    IGPGHandler, GPGVerificationError, IGPGKeySet, IPersonSet,
    IEmailAddressSet, IComponentSet, ISectionSet)

from canonical.lp import dbschema

class UploaderTester:
    """Methods to prepare the LP DB to recieve the testing uploads."""
    def __init__(self, ztm, log, options, uploader_team,
                 keyring=None):
        """Stores passed information locally and import keyring if necessary."""
        self.ztm = ztm
        self.log = log
        self.options = options
        self.uploader_team = uploader_team
        if keyring:
            self.log.info("Import Keyring at %s", keyring)
            self._load_keyring(keyring)

    def _load_keyring(self, keyring):
        """Loads a passed keyring using IGpgHandler utility."""
        getUtility(IGPGHandler).importKeyringFile(keyring)

    def _verify_signature(self, content):
        """Verify a GPG signed message.

        Returns an IPymeSignature object when it succeeded or None
        if it fails.
        """
        self.log.debug("Verifying Signature:")

        try:
            sig = getUtility(IGPGHandler).verifySignature(content)
        except GPGVerificationError, info:
            self.log.critical(info)
            return None

        return sig

    def _extract_signer_address(self, content):
        """Extract signer address from a .dsc or .changes file

        This method will iterate through the content lines and try to
        find either a Changed-By field or a  Maintainer field to
        extract the signer address from. The Changed-By field has
        precedence, since .changes files have both of them, but the
        signer is the one in Changed-By.
        """
        name = addr = None
        for line in content.splitlines():
            if line.startswith("Changed-By:"):
                name, addr = rfc822.parseaddr(line[len("Changed-By:"):].strip())
                break
            elif line.startswith("Maintainer:"):
                name, addr = rfc822.parseaddr(line[len("Maintainer:"):].strip())
        if name is None:
            raise ValueError, "No valid signer address found field found"
        return name, addr

    def ensure_signer(self, content):
        """Ensure Signer is present in LPDB as a valid person.

        Verify signature using IGPGHandler, find out if the signer is
        a 'valid person' in LP. Whether is present or not, inspect the
        changes_content for new personal information (basically new email)
        and create or upgrade the personal registry.
        """
        sig = self._verify_signature(content)
        if not sig:
            self.log.debug("Could not verify the signature, check your "
                           "connection to the keyserver or your keyring.")
            return

        self.log.debug("Fingerprint -> %s", sig.fingerprint)
        # begin a launchpad transaction
        self.ztm.begin()
        # retrieve key from LPDB
        key = getUtility(IGPGKeySet).getByFingerprint(sig.fingerprint)
        # we assume all keys have an owner.
        if key:
            self.log.debug("User %s is already present in LPDB",
                           key.owner.name)
            return
        # key not found, need to add
        self.log.debug("Key is not present, creating it.")
        # Protect LPDB writes
        try:
            # retrieve user details from changes file
            displayname, email = self._extract_signer_address(content)
            # create person ...
            user = getUtility(IPersonSet).ensurePerson(email, displayname)
            if user is None:
                raise ValueError('Could not create user %s, %s'
                                  % (displayname, email))

            if user.preferredemail is None:
                # ensure the user has preferred email address
                # XXX cprov 20060126: We really don't want to set
                # the preferred email of a person w/o proper feedback
                # See further info in bug # 29790
                user_email = getUtility(IEmailAddressSet).getByEmail(email)
                user_email.status = dbschema.EmailAddressStatus.PREFERRED
                # ensure the DB content is modified immediately
                self.ztm.commit()
                self.log.info('Setting PREFERRED email to: %s'
                              % user.preferredemail.email)

            # add user to the uploader_test team
            self.uploader_team.addMember(user)

            # create a PymeKey to wrap the handy attributes, it's necessary
            # because we are based in a local keyring. We may use a keyserver
            # in the future and replace it by a importKey()
            key = PymeKey(sig.fingerprint)
            # XXX cprov 20051130: missing PymeKey attribute
            # IPymeKey.active is missing from original PymeKey implementation
            lpkey = getUtility(IGPGKeySet).new(
                ownerID=user.id, keyid=key.keyid,
                fingerprint=key.fingerprint,
                algorithm=dbschema.GPGKeyAlgorithm.items[key.algorithm],
                keysize=key.keysize, can_encrypt=key.can_encrypt)
        except (KeyError, SQLObjectIntegrityError), info:
            self.ztm.abort()
            self.log.critical(str(info))
        else:
            self.log.info("%s, %s, 0x%s", user.displayname, email, lpkey.keyid)
            self.ztm.commit()


class FTPURLError(Exception):
    """Local exception to mask FTPURL errors and information mismatch."""


class FTPURL:
    """Stores and parses FTP url schema.

    It expect something like: ftp://user:passwd@host:port/path/
    Providing those same named attributes.
    """
    def __init__(self, url):
        scheme, rest = urllib.splittype(url)
        if scheme != "ftp":
            raise FTPURLError("Non-FTP URL provided")
        rest, self.path = urllib.splithost(rest)
        userpasswd, hostport = urllib.splituser(rest)
        self.host, self.port = urllib.splitport(hostport)
        if userpasswd:
            self.user, self.passwd = urllib.splitpasswd(userpasswd)
        else:
            self.user = self.passwd = None


class RSyncError(Exception):
    """Mask any rsync method errors."""

def rsync_files(orig_url, dest_url, includes=None):
    """Wraps the rsync app as a subprocess.

    Use compressed transfer mode, accepts an optional list of includes.
    Raises RsyncError if something goes wrong.
    """
    if includes is not None:
        options = " ".join(["--include '%s'" % expr for expr in includes])
        options += " --exclude '*'"
    else:
        options = ""
    cmd = "rsync -vz %s '%s' '%s'" % (options, orig_url, dest_url)
    devnull = open("/dev/null", "w")
    process = subprocess.Popen(cmd, stdout=devnull, shell=True)
    devnull.close()
    if process.wait() != 0:
        raise RSyncError

def rsync_list_filenames(url):
    """Return a list of filenames available for rsync in a given url."""
    cmd = "rsync -z '%s'" % url
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    filenames = []
    for line in process.stdout:
        filenames.append(line.split()[-1])
    if process.wait() != 0:
        raise RSyncError
    return filenames

def ftp_send_files(orig_dir, ftp_url_obj):
    """Send all files from the given directory to the ftp server URL"""
    # XXX gustavo 20051210: Do we want to keep the connection open
    # to improve the performance? This would change the way that
    # the poppy FTP server stores them though.
    ftp = ftplib.FTP()
    ftp.connect(ftp_url_obj.host, ftp_url_obj.port)
    ftp.login(ftp_url_obj.user, ftp_url_obj.passwd)
    ftp.cwd(ftp_url_obj.path)
    for filename in os.listdir(orig_dir):
        file = open(os.path.join(orig_dir, filename))
        ftp.storbinary("STOR " + filename, file)
        file.close()
    ftp.quit()

def read_files_from_changes(filename):
    """Return a list of useful info from the 'Files:' Changesfiles section.

    Return a list of tuples containing (files, component, section).
    """
    file = open(filename)
    files = []
    proto_secs = []
    started = False
    for line in file:
        line = line.rstrip()
        if line:
            if started:
                if line[0] != " ":
                    break
                # CKSUM SIZE COMP/SECT PRIORITY FILENAME
                ck, s, proto_sec, priority, filename = line.strip().split()
                proto_secs.append(proto_sec)
                files.append(filename)
            elif line == "Files:":
                started = True
    # XXX cprov 20051206: assuming component & section are the same for all
    # files within a change, which is reasonable.
    proto_sec = set(proto_secs).pop()

    # extract component and section from a collapsed form, use 'main' component
    # if it was omitted.
    if '/' in proto_sec:
        component, section = proto_sec.split('/')
    else:
        component = 'main'
        section = proto_sec

    return files, component, section


def main():
    """Initiate and run the 'rsyncing' cycle importing sources via poppy."""
    # Parse command-line arguments
    parser = optparse.OptionParser()
    logger_options(parser)

    parser.add_option("-k", "--keyring", metavar="FILENAME",
                      help="OpenPGP Key Ring file to be imported.")

    parser.add_option("-s", "--sleep", metavar="SECONDS",type="int",
                      help="Wait given seconds between uploads")

    parser.add_option("-p", "--packages", metavar="PKGLIST",
                      help="File containing a list of package names")

    options, args = parser.parse_args()

    if len(args) != 2:
        sys.exit("Usage: uploader-test.py <rsync url> <ftp url>")

    rsync_url, ftp_url = args

    log = logger(options, "uploader-test")


    # rsync gives different treatment for non-/ terminated urls,
    # we always want it /-terminated
    if not rsync_url.endswith('/'):
        rsync_url += '/'
    # check on directory deep in the passed url
    rsync_url += '**/'

    try:
        ftp_url_obj = FTPURL(ftp_url)
    except FTPURLError, e:
        log.error(str(e))
        sys.exit(1)

    # Launchpad required setup
    ztm = initZopeless(dbuser=config.uploader.dbuser)
    execute_zcml_for_scripts()

    log.debug("Acquiring lock")
    lock = GlobalLock('/var/lock/launchpad-uploader-test.lock')
    lock.acquire(blocking=True)

    try:
        uploader_team = getUtility(IPersonSet).getByName('ubuntu-team')

        if not uploader_team:
            log.critical("No 'ubuntu-team' found, insert the "
                         "required DB data")
            sys.exit(1)

        tester = UploaderTester(ztm, log, options, uploader_team,
                                keyring=options.keyring)

        log.info("Fetching list of files with .changes suffix")
        changes_filenames = rsync_list_filenames(rsync_url + "*.changes")

        # attempt to handle only list of previously selected packages
        if options.packages:
            log.info("Comparing with selected files from '%s'"
                     % options.packages)
            # fetch list from a file
            packagenames = [pkgname.strip() for pkgname in
                            open(options.packages).readlines()]

            changes_selected = []
            for changes_filename in changes_filenames:
                # changes_file is named as :
                #    <packagename>_<version>_source.changes
                # XXX cprov 20060108: it might be an expensive statement
                # depending on the selected list size, but at least is
                # performed only once.
                packagename = changes_filename.split('_')[0]
                if packagename in packagenames:
                    # append the filename from the main list if it's
                    # present in the selected list.
                    changes_selected.append(changes_filename)
        else:
            changes_selected = changes_filenames

        for changes_filename in changes_selected:

            temp_dir = tempfile.mkdtemp("-rsync-to-ftp")
            log.info("Using temporary directory at %s" % temp_dir)

            try:
                changes_filepath = os.path.join(temp_dir, changes_filename)

                log.info("Fetching %s" % changes_filename)
                rsync_files(rsync_url + changes_filename, temp_dir)

                changes_file = open(changes_filepath)
                tester.ensure_signer(changes_file.read())
                changes_file.close()

                log.info("Extracting files list...")
                files, component, section = read_files_from_changes(
                    changes_filepath)
                # Component and section could be created within
                # the upload policy domain.
                # See further info in bug # 29790
                getUtility(IComponentSet).ensure(component)
                getUtility(ISectionSet).ensure(section)

                log.info("Downloading additional files...")
                rsync_files(rsync_url + '*', temp_dir, includes=files)

                log.info("Uploading to FTP server...")
                ftp_send_files(temp_dir, ftp_url_obj)

                log.info("Done.")

            finally:
                log.info("Removing temporary directory...")
                shutil.rmtree(temp_dir)

            # wait some time between uploads
            if options.sleep:
                time.sleep(options.sleep)

        log.info("Finished.")

    finally:
        log.debug("Releasing lock")
        lock.release()

if __name__ == '__main__':
    main()




