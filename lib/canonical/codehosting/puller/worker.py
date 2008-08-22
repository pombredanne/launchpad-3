# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import httplib
import os
import shutil
import socket
import sys
import urllib2

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.errors import (
    BzrError, NotBranchError, NotStacked, ParamikoNotPresent,
    UnknownFormatError, UnstackableBranchFormat, UnstackableRepositoryFormat,
    UnsupportedFormatError)
from bzrlib.progress import DummyProgress
from bzrlib.transport import get_transport
import bzrlib.ui

from canonical.config import config
from canonical.codehosting import ProgressUIFactory
from canonical.codehosting.bzrutils import ensure_base
from canonical.codehosting.puller import get_lock_id_for_branch_id
from canonical.codehosting.transport import get_puller_server
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp import errorlog
from canonical.launchpad.webapp.uri import URI, InvalidURIError


__all__ = [
    'BadUrl',
    'BadUrlFile',
    'BadUrlLaunchpad',
    'BadUrlSsh',
    'BranchReferenceLoopError',
    'BranchReferenceForbidden',
    'BranchReferenceValueError',
    'get_canonical_url_for_branch_name',
    'install_worker_ui_factory',
    'MirroredURLChecker',
    'PullerWorker',
    'PullerWorkerProtocol',
    'URLChecker',
    ]


class BadUrl(Exception):
    """Tried to mirror a branch from a bad URL."""


class BadUrlSsh(BadUrl):
    """Tried to mirror a branch from sftp or bzr+ssh."""


class BadUrlLaunchpad(BadUrl):
    """Tried to mirror a branch from launchpad.net."""


class BadUrlScheme(BadUrl):
    """Found a URL with an untrusted scheme."""
    def __init__(self, scheme, url):
        BadUrl.__init__(self, scheme, url)
        self.scheme = scheme


class BranchReferenceForbidden(Exception):
    """Trying to mirror a branch reference and the branch type does not allow
    references.
    """


class BranchReferenceLoopError(Exception):
    """Encountered a branch reference cycle.

    A branch reference may point to another branch reference, and so on. A
    branch reference cycle is an infinite loop of references.
    """


def get_canonical_url_for_branch_name(unique_name):
    """Custom implementation of canonical_url(branch) for error reporting.

    The actual `canonical_url` function cannot be used because we do not have
    access to real content objects.
    """
    if config.vhosts.use_https:
        scheme = 'https'
    else:
        scheme = 'http'
    hostname = config.vhost.code.hostname
    return scheme + '://' + hostname + '/~' + unique_name


class PullerWorkerProtocol:
    """The protocol used to communicate with the puller scheduler.

    This protocol notifies the scheduler of events such as startMirroring,
    mirrorSucceeded and mirrorFailed.
    """

    def __init__(self, output):
        self.out_stream = output

    def sendNetstring(self, string):
        self.out_stream.write('%d:%s,' % (len(string), string))

    def sendEvent(self, command, *args):
        self.sendNetstring(command)
        self.sendNetstring(str(len(args)))
        for argument in args:
            self.sendNetstring(str(argument))

    def startMirroring(self):
        self.sendEvent('startMirroring')

    def mirrorSucceeded(self, last_revision):
        self.sendEvent('mirrorSucceeded', last_revision)

    def mirrorFailed(self, message, oops_id):
        self.sendEvent('mirrorFailed', message, oops_id)

    def progressMade(self):
        self.sendEvent('progressMade')


def identical_formats(branch_one, branch_two):
    """Check if two branches have the same bzrdir, repo, and branch formats.
    """
    # XXX AndrewBennetts 2006-05-18 bug=45277:
    # comparing format objects is ugly.
    b1, b2 = branch_one, branch_two
    return (
        b1.bzrdir._format.__class__ == b2.bzrdir._format.__class__ and
        b1.repository._format.__class__ == b2.repository._format.__class__ and
        b1._format.__class__ == b2._format.__class__
    )


class BranchOpener(object):
    """A `BranchOpener` opens branches with an eye to safety.

    The external interface is `open`.  Subclasses must override
    `shouldFollowReferences` and `checkOneURL`, and tests override
    `followReference` and `openBranch`.
    """

    def open(self, url):
        """Open the Bazaar branch at url, first checking for safety.

        What safety means is defined by a subclasses `followReference` and
        `checkOneURL` methods.
        """
        self.checkSource(url)
        return self.openBranch(url)

    def followReference(self, url):
        """Get the branch-reference value at the specified url.

        This exists as a separate method only to be overriden in unit tests.
        """
        bzrdir = BzrDir.open(url)
        return bzrdir.get_branch_reference()

    def openBranch(self, url):
        """Open the Bazaar at `url`.

        This exists as a separate method only to be overriden in unit tests.
        """
        return Branch.open(url)

    def checkSource(self, url):
        """Check `url` is safe to pull a branch from.

        :param url: URL of the location to check.
        :raise BranchReferenceForbidden: the source location contains a branch
            reference, and branch references are not allowed for this branch
            type.
        :raise BranchReferenceLoopError: the source location contains a branch
            reference that leads to a reference cycle.
        :raise BadUrl: `checkOneURL` is expected to raise this or a subclass
            when it finds a URL it deems to be unsafe.
        """
        self.checkOneURL(url)
        traversed_references = set()
        while True:
            reference_value = self.followReference(url)
            if reference_value is None:
                break
            if not self.shouldFollowReferences():
                raise BranchReferenceForbidden(reference_value)
            traversed_references.add(url)
            if reference_value in traversed_references:
                raise BranchReferenceLoopError()
            self.checkOneURL(reference_value)
            url = reference_value

    def shouldFollowReferences(self):
        """Whether we traverse references when mirroring.

        Subclasses must override this method.

        If we encounter a branch reference and this returns false, an error is
        raised.

        :returns: A boolean to indicate whether to follow a branch reference.
        """
        raise NotImplementedError(self.shouldFollowReferences)

    def checkOneURL(self, url):
        """Check the safety of the source URL.

        Subclasses must override this method.

        :param url: The source URL to check.
        :raise BadUrl: subclasses are expected to raise this or a subclass
            when it finds a URL it deems to be unsafe.
        """
        raise NotImplementedError(self.checkOneURL)


class HostedBranchOpener(BranchOpener):
    """Specialization of `BranchOpener` for HOSTED branches.

    In summary:

     - don't follow references,
     - assert we're pulling from a lp-hosted:/// URL.
    """

    def shouldFollowReferences(self):
        """See `BranchOpener.shouldFollowReferences`.

        We do not traverse references for HOSTED branches because that may
        cause us to connect to remote locations, which we do not allow because
        we want hosted branches to be mirrored quickly.
        """
        return False

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        If the URL we are mirroring from is anything but a
        lp-hosted:///~user/project/branch URL, something has gone badly wrong,
        so we raise AssertionError if that's happened.
        """
        uri = URI(url)
        if uri.scheme != 'lp-hosted':
            raise AssertionError(
                "Non-hosted url %r for hosted branch." % url)


class MirroredBranchOpener(BranchOpener):
    """Specialization of `BranchOpener` for MIRRORED branches.

    In summary:

     - follow references,
     - only open non-Launchpad http: and https: URLs.
    """

    def shouldFollowReferences(self):
        """See `BranchOpener.shouldFollowReferences`.

        We traverse branch references for MIRRORED branches because they
        provide a useful redirection mechanism and we want to be consistent
        with the bzr command line.
        """
        return True

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        We refuse to mirror from Launchpad or a ssh-like or file URL.
        """
        uri = URI(url)
        launchpad_domain = config.vhost.mainsite.hostname
        if uri.underDomain(launchpad_domain):
            raise BadUrlLaunchpad(url)
        if uri.scheme in ['sftp', 'bzr+ssh']:
            raise BadUrlSsh(url)
        elif uri.scheme not in ['http', 'https']:
            raise BadUrlScheme(uri.scheme, url)


class ImportedBranchOpener(BranchOpener):
    """Specialization of `BranchOpener` for IMPORTED branches.

    In summary:

     - don't follow references,
     - assert the URLs start with the prefix we expect for imported branches.
    """

    def shouldFollowReferences(self):
        """See `BranchOpener.shouldFollowReferences`.

        We do not traverse references for IMPORTED branches because the
        code-import system should never produce branch references.
        """
        return False

    def checkOneURL(self, url):
        """See `BranchOpener.checkOneURL`.

        If the URL we are mirroring from does not start how we expect the pull
        URLs of import branches to start, something has gone badly wrong, so
        we raise AssertionError if that's happened.
        """
        if not url.startswith(config.launchpad.bzr_imports_root_url):
            raise AssertionError(
                "Bogus URL for imported branch: %r" % url)


class PullerWorker:
    """This class represents a single branch that needs mirroring.

    It has a source URL, a destination URL, a database id, a unique name and a
    status client which is used to report on the mirror progress.
    """

    def _checkerForBranchType(self, branch_type):
        """Return an instance of an appropriate subclass of `URLChecker`."""
        if branch_type == BranchType.HOSTED:
            return HostedBranchOpener()
        elif branch_type == BranchType.MIRRORED:
            return MirroredBranchOpener()
        elif branch_type == BranchType.IMPORTED:
            return ImportedBranchOpener()
        else:
            raise AssertionError(
                "Unexpected branch type: %r" % branch_type)

    def __init__(self, src, dest, branch_id, unique_name, branch_type,
                 protocol, branch_opener=None, oops_prefix=None):
        """Construct a `PullerWorker`.

        :param src: The URL to pull from.
        :param dest: The URL to pull into.
        :param branch_id: The database ID of the branch we're pulling.
        :param unique_name: The unique_name of the branch we're pulling
            (without the tilde).
        :param branch_type: A member of the BranchType enum.  It is expected
            that tests that do not depend on its value will pass None.
        :param protocol: An instance of `PullerWorkerProtocol`.
        :param branch_opener: An instance of `BranchOpener`.  If not passed, one will
            be chosen based on the value of `branch_type`.
        :param oops_prefix: An oops prefix to pass to `setOopsToken` on the
            global ErrorUtility.
        """
        self.source = src
        self.dest = dest
        self.branch_id = branch_id
        self.unique_name = unique_name
        self.branch_type = branch_type
        if branch_opener is None:
            branch_opener = self._checkerForBranchType(branch_type)
        self.branch_opener = branch_opener
        self.protocol = protocol
        if protocol is not None:
            self.protocol.branch_id = branch_id
        if oops_prefix is not None:
            errorlog.globalErrorUtility.setOopsToken(oops_prefix)

    def _openSourceBranch(self, source):
        """Open the branch to pull from.

        This only exists as a separate method to be overriden in tests.
        """
        return Branch.open(source)

    def _mirrorToDestBranch(self, source_branch):
        """Open the branch to pull to, creating a new one if necessary.

        Useful to override in tests.
        """
        try:
            branch = BzrDir.open(self.dest).open_branch()
        except NotBranchError:
            # Make a new branch in the same format as the source branch.
            branch = self._createDestBranch(source_branch)
        else:
            # Check that destination branch is in the same format as the
            # source.
            if identical_formats(source_branch, branch):
                # The destination exists, and is in the same format.  So all
                # we need to do is update it.

                # If the branch is locked, try to break it.  Our special UI
                # factory will allow the breaking of locks that look like they
                # were left over from previous puller worker runs.  We will
                # block on other locks and fail if they are not broken before
                # the timeout expires (currently 5 minutes).
                if branch.get_physical_lock_status():
                    branch.break_lock()

                # Make sure the mirrored branch is stacked the same way as the
                # source branch.  Note that we expect this to be fairly
                # common, as, as of r6889, it is possible for a branch to be
                # pulled before the stacking information is set at all.
                try:
                    stacked_on_url = source_branch.get_stacked_on_url()
                except (UnstackableRepositoryFormat, UnstackableBranchFormat,
                        NotStacked):
                    stacked_on_url = None
                try:
                    branch.set_stacked_on_url(stacked_on_url)
                except (UnstackableRepositoryFormat, UnstackableBranchFormat):
                    if stacked_on_url is not None:
                        raise AssertionError(
                            "Couldn't set stacked_on_url %r" % stacked_on_url)
                branch.pull(source_branch, overwrite=True)
            else:
                # The destination is in a different format to the source, so
                # we'll delete it and mirror from scratch.
                branch = self._createDestBranch(source_branch)
        return branch

    def _createDestBranch(self, source_branch):
        """Create the branch to pull to, and copy the source's contents."""
        if os.path.exists(self.dest):
            shutil.rmtree(self.dest)
        ensure_base(get_transport(self.dest))
        bzrdir = source_branch.bzrdir
        bzrdir.clone(self.dest, preserve_stacking=True)
        return Branch.open(self.dest)

    def _record_oops(self, message=None):
        """Record an oops for the current exception.

        This must only be called while handling an exception.

        :param message: custom explanatory error message. Do not use
            str(exception) to fill in this parameter, it should only be set
            when a human readable error has been explicitly generated.
        """
        request = errorlog.ScriptRequest([
            ('branch_id', self.branch_id), ('source', self.source),
            ('dest', self.dest), ('error-explanation', str(message))])
        request.URL = get_canonical_url_for_branch_name(self.unique_name)
        errorlog.globalErrorUtility.raising(sys.exc_info(), request)
        return request.oopsid

    def _mirrorFailed(self, error):
        oops_id = self._record_oops(error)
        self.protocol.mirrorFailed(error, oops_id)

    def mirrorWithoutChecks(self):
        """Mirror the source branch to the destination branch.

        This method doesn't do any error handling or send any messages via the
        reporting protocol -- a "naked mirror", if you will. This is
        particularly useful for tests that want to mirror a branch and be
        informed immediately of any errors.
        """
        server = get_puller_server()
        server.setUp()
        try:
            source_branch = self.branch_opener.open(self.source)
            return self._mirrorToDestBranch(source_branch)
        finally:
            server.tearDown()

    def mirror(self):
        """Open source and destination branches and pull source into
        destination.
        """
        self.protocol.startMirroring()
        try:
            dest_branch = self.mirrorWithoutChecks()
        # add further encountered errors from the production runs here
        # ------ HERE ---------
        #
        except urllib2.HTTPError, e:
            msg = str(e)
            if int(e.code) == httplib.UNAUTHORIZED:
                # Maybe this will be caught in bzrlib one day, and then we'll
                # be able to get rid of this.
                # https://launchpad.net/products/bzr/+bug/42383
                msg = "Authentication required."
            self._mirrorFailed(msg)

        except socket.error, e:
            msg = 'A socket error occurred: %s' % str(e)
            self._mirrorFailed(msg)

        except UnsupportedFormatError, e:
            msg = ("Launchpad does not support branches from before "
                   "bzr 0.7. Please upgrade the branch using bzr upgrade.")
            self._mirrorFailed(msg)

        except UnknownFormatError, e:
            self._mirrorFailed(e)

        except (ParamikoNotPresent, BadUrlSsh), e:
            msg = ("Launchpad cannot mirror branches from SFTP and SSH URLs."
                   " Please register a HTTP location for this branch.")
            self._mirrorFailed(msg)

        except BadUrlLaunchpad:
            msg = "Launchpad does not mirror branches from Launchpad."
            self._mirrorFailed(msg)

        except BadUrlScheme, e:
            msg = "Launchpad does not mirror %s:// URLs." % e.scheme
            self._mirrorFailed(msg)

        except NotBranchError, e:
            hosted_branch_error = NotBranchError("lp:~%s" % self.unique_name)
            message_by_type = {
                BranchType.HOSTED: str(hosted_branch_error),
                BranchType.IMPORTED: "Not a branch.",
                }
            msg = message_by_type.get(self.branch_type, str(e))
            self._mirrorFailed(msg)

        except BranchReferenceForbidden, e:
            msg = ("Branch references are not allowed for branches of type "
                   "%s." % (self.branch_type.title,))
            self._mirrorFailed(msg)

        except BranchReferenceLoopError, e:
            msg = "Circular branch reference."
            self._mirrorFailed(msg)

        except BzrError, e:
            self._mirrorFailed(e)

        except InvalidURIError, e:
            self._mirrorFailed(e)

        except (KeyboardInterrupt, SystemExit):
            # Do not record OOPS for those exceptions.
            raise

        else:
            last_rev = dest_branch.last_revision()
            self.protocol.mirrorSucceeded(last_rev)

    def __eq__(self, other):
        return self.source == other.source and self.dest == other.dest

    def __repr__(self):
        return ("<PullerWorker source=%s dest=%s at %x>" %
                (self.source, self.dest, id(self)))


class WorkerProgressBar(DummyProgress):
    """A progress bar that informs a PullerWorkerProtocol of progress."""

    def _event(self, *args, **kw):
        """Inform the PullerWorkerProtocol of progress.

        This method is attached to the class as all of the progress bar
        methods: tick, update, child_update, clear and note.
        """
        self.puller_worker_protocol.progressMade()

    tick = _event
    update = _event
    child_update = _event
    clear = _event
    note = _event

    def child_progress(self, **kwargs):
        """As we don't care about nesting progress bars, return self."""
        return self


class PullerWorkerUIFactory(ProgressUIFactory):
    """An UIFactory that always says yes to breaking locks."""

    def get_boolean(self, prompt):
        """If we're asked to break a lock like a stale lock of ours, say yes.
        """
        assert prompt.startswith('Break lock'), (
            "Didn't expect prompt %r" % (prompt,))
        branch_id = self.puller_worker_protocol.branch_id
        if get_lock_id_for_branch_id(branch_id) in prompt:
            return True
        else:
            return False


def install_worker_ui_factory(puller_worker_protocol):
    """Install a special UIFactory for puller workers.

    Our factory does two things:

    1) Create progress bars that inform a PullerWorkerProtocol of progress.
    2) Break locks if and only if they appear to be stale locks
       created by another puller worker process.
    """
    def factory(*args, **kw):
        r = WorkerProgressBar(*args, **kw)
        r.puller_worker_protocol = puller_worker_protocol
        return r
    bzrlib.ui.ui_factory = PullerWorkerUIFactory(factory)
    bzrlib.ui.ui_factory.puller_worker_protocol = puller_worker_protocol
