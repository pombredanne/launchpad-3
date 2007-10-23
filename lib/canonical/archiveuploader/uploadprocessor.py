# Copyright 2006 Canonical Ltd.  All rights reserved.
#

"""Code for 'processing' 'uploads'. Also see nascentupload.py.

Uploads are directories in the 'incoming' queue directory. They may have
arrived manually from a distribution contributor, via a poppy upload, or
they may have come from a build.

Within an upload, we may find no changes file, one, or several. One is
the usual number. To process the upload, we process each changes file
in turn. These changes files may be within a structure of sub-directories,
in which case we extract information from the names of these, to calculate
which distribution and which PPA are being uploaded to.

To process a changes file, we make checks such as that the other files
referenced by it are present, formatting is valid, signatures are correct,
checksums match, and that the .changes file represents an upload which makes
sense, eg. it is not a binary for which we have no source, or an older
version than already exists in the same target distroseries pocket.

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

import os
import shutil

from zope.component import getUtility

from canonical.archiveuploader.nascentupload import (
    NascentUpload, FatalUploadError, EarlyReturnUploadError)
from canonical.archiveuploader.uploadpolicy import (
    findPolicyByOptions, UploadPolicyError)
from canonical.launchpad.interfaces import (
    ArchivePurpose, IDistributionSet, IPersonSet, NotFoundError)

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


class UploadPathError(Exception):
    """This exception happened when parsing the upload path."""

class PPAUploadPathError(Exception):
    """Exception when parsing a PPA upload path."""

class UploadProcessor:
    """Responsible for processing uploads. See module docstring."""

    def __init__(self, options, ztm, log):
        self.options = options
        self.ztm = ztm
        self.log = log
        self.last_processed_upload = None

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

        Return .changes files sorted with *_source.changes first. This
        is important to us, as in an upload containing several changes files,
        it's possible the binary ones will depend on the source ones, so
        the source ones should always be considered first.
        """
        changes_files = []

        for dirpath, dirnames, filenames in os.walk(upload_path):
            relative_path = dirpath[len(upload_path) + 1:]
            for filename in filenames:
                if filename.endswith(".changes"):
                    changes_files.append(os.path.join(relative_path, filename))
        return self.orderFilenames(changes_files)

    def processChangesFile(self, upload_path, changes_file):
        """Process a single changes file.

        This is done by obtaining the appropriate upload policy (according
        to command-line options and the value in the .distro file beside
        the upload, if present), creating a NascentUpload object and calling
        its process method.

        We obtain the context for this processing from the relative path,
        within the upload folder, of this changes file. This influences
        our creation both of upload policy and the NascentUpload object.

        See nascentupload.py for the gory details.

        Returns a value from UploadStatusEnum, or re-raises an exception
        from NascentUpload.
        """
        # Calculate the distribution from the path within the upload
        # Reject the upload since we could not process the path,
        # Store the exception information as a rejection message.
        relative_path = os.path.dirname(changes_file)
        error = None
        try:
            distribution, suite_name, archive = self.getDistributionAndArchive(
                relative_path)
        except UploadPathError, e:
            # pick some defaults to create the NascentUploap() object.
            # We will be rejecting the upload so it doesn matter much.
            distribution = getUtility(IDistributionSet)['ubuntu']
            suite_name = None
            archive = distribution.main_archive
            error = str(e)
        except PPAUploadPathError, e:
            # Again, pick some defaults but leave a hint for the rejection
            # emailer that it was a PPA failure.
            distribution = getUtility(IDistributionSet)['ubuntu']
            suite_name = None
            archive = distribution.main_archive
            # This is fine because the transaction will be aborted when
            # the rejection happens.
            archive.purpose = ArchivePurpose.PPA
            error = str(e)

        self.log.debug("Finding fresh policy")
        self.options.distro = distribution.name
        policy = findPolicyByOptions(self.options)
        policy.archive = archive
        # DistroSeries overriding respect the following precedence:
        #  1. process-upload.py command-line option (-r),
        #  2. upload path,
        #  3. changesfile 'Distribution' field.
        if suite_name is not None:
            policy.setDistroSeriesAndPocket(suite_name)

        # The path we want for NascentUpload is the path to the folder
        # containing the changes file (and the other files referenced by it).
        changesfile_path = os.path.join(upload_path, changes_file)
        upload = NascentUpload(changesfile_path, policy, self.log)

        # Store archive lookup error in the upload if it was the case.
        if error is not None:
            upload.reject(error)

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
            except EarlyReturnUploadError:
                # An error occurred that prevented further error collection,
                # add this fact to the list of errors.
                upload.reject(
                    "Further error processing not possible because of "
                    "a critical previous error.")
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

            # XXX julian 2007-05-25 bug=29744:
            # When bug #29744 is fixed (zopeless mails should only be sent
            # when transaction is committed) this will cause any emails sent
            # sent by do_reject to be lost.
            notify = True
            if self.options.dryrun or self.options.nomails:
                notify = False
            if upload.is_rejected:
                result = UploadStatusEnum.REJECTED
                upload.do_reject(notify)
                self.ztm.abort()
            else:
                successful = upload.do_accept(notify=notify)
                if not successful:
                    result = UploadStatusEnum.REJECTED
                    self.log.info("Rejection during accept. "
                                  "Aborting partial accept.")
                    self.ztm.abort()

            if upload.is_rejected:
                self.log.warn("Upload was rejected:")
                for msg in upload.rejections:
                    self.log.warn("\t%s" % msg)

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

    def orderFilenames(self, fnames):
        """Order filenames, sorting *_source.changes before others.

        Aside from that, a standard string sort.
        """
        def sourceFirst(filename):
            return (not filename.endswith("_source.changes"), filename)

        return sorted(fnames, key=sourceFirst)

    def getDistributionAndArchive(self, relative_path):
        """Locate the distribution and archive for the upload.

        We do this by analysing the path to which the user has uploaded,
        ie. the relative path within the upload folder to the changes file.

        The valid paths are:
        '' - default distro, ubuntu
        '<distroname>' - given distribution
        '~<personname>/<distroname>/[distroseriesname]' - given ppa,
          distribution and optionally a distroseries.

        I raises UploadPathError if something was wrong when parsing it.

        On success it returns a tuple of IDistribution, suite-name,
        IArchive for the given path, where the second field can be None.
        """
        parts = relative_path.split(os.path.sep)
        first_path = parts[0]

        # Empty distroseries override by default.
        suite_name = None

        # Distribution name only, or nothing
        if len(parts) == 1:
            distribution_name = first_path
            # fallback to ubuntu
            if not distribution_name:
                distribution_name = 'ubuntu'

            distribution = getUtility(IDistributionSet).getByName(
                distribution_name)
            if not distribution:
                raise UploadPathError(
                    "Could not find distribution '%s'" % distribution_name)
            archive = distribution.main_archive

        # PPA upload (~<person>/<distro>/[distroseries])
        elif len(parts) <= 3:
            if not first_path.startswith('~'):
                raise PPAUploadPathError(
                    "PPA upload path must start with '~'.")

            # Skip over ~
            person_name = first_path[1:]
            person = getUtility(IPersonSet).getByName(person_name)
            if person is None:
                raise PPAUploadPathError(
                    "Could not find person '%s'" % person_name)

            distribution_name = parts[1]
            distribution = getUtility(IDistributionSet).getByName(
                distribution_name)
            if distribution is None:
                raise PPAUploadPathError(
                    "Could not find distribution '%s'" % distribution_name)

            archive = person.archive
            if archive is None:
                raise PPAUploadPathError(
                    "Could not find PPA for '%s'" % person_name)

            if not archive.enabled:
                raise PPAUploadPathError(
                    "%s is disabled" % archive.title)

            if archive.distribution != distribution:
                raise PPAUploadPathError(
                    "%s only supports uploads to '%s'"
                    % (archive.title, archive.distribution.name))

            if len(parts) > 2:
                suite_name = parts[2]
                # Check if the given suite name is valid.
                # We will return the suite_name string simply.
                try:
                    suite = distribution.getDistroSeriesAndPocket(suite_name)
                except NotFoundError:
                    raise PPAUploadPathError(
                        "Could not find suite '%s'" % suite_name)
        else:
            raise UploadPathError(
                "Path mismatch '%s'. Use ~<person>/<distro>/[distroseries]/"
                "[files] for PPAs and <distro>/[files] for normal uploads."
                % (relative_path))

        return (distribution, suite_name, archive)

