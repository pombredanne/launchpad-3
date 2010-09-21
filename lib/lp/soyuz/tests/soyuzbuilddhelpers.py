# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mock Build objects for tests soyuz buildd-system."""

__metaclass__ = type

__all__ = [
    'MockBuilder',
    'LostBuildingBrokenSlave',
    'BrokenSlave',
    'OkSlave',
    'BuildingSlave',
    'AbortedSlave',
    'WaitingSlave',
    'AbortingSlave',
    ]

from StringIO import StringIO
import xmlrpclib

from twisted.internet import defer

from lp.buildmaster.interfaces.builder import CannotFetchFile
from lp.buildmaster.model.builder import (
    rescueBuilderIfLost,
    updateBuilderStatus,
    )
from lp.soyuz.model.binarypackagebuildbehavior import (
    BinaryPackageBuildBehavior,
    )
from lp.testing.sampledata import I386_ARCHITECTURE_NAME

# XXX: Almost everything in this module will need to be revisited & perhaps
# deleted now that we have new APIs for BuilderSlave.

class MockBuilder:
    """Emulates a IBuilder class."""

    def __init__(self, name, slave, behavior=None):
        if behavior is None:
            self.current_build_behavior = BinaryPackageBuildBehavior(None)
        else:
            self.current_build_behavior = behavior

        self.slave = slave
        self.builderok = True
        self.manual = False
        self.url = 'http://fake:0000'
        slave.urlbase = self.url
        self.name = name
        self.virtualized = True

    def failBuilder(self, reason):
        self.builderok = False
        self.failnotes = reason

    def slaveStatusSentence(self):
        return self.slave.status()

    def verifySlaveBuildCookie(self, slave_build_id):
        return self.current_build_behavior.verifySlaveBuildCookie(
            slave_build_id)

    def cleanSlave(self):
        # XXX: This should not print anything. The print is only here to make
        # doc/builder.txt a meaningful test.
        print 'Cleaning slave'
        return self.slave.clean()

    def requestAbort(self):
        # XXX: This should not print anything. The print is only here to make
        # doc/builder.txt a meaningful test.
        print 'Aborting slave'
        return self.slave.abort()

    def resumeSlave(self, logger):
        return ('out', 'err')

    def checkSlaveAlive(self):
        pass

    def rescueIfLost(self, logger=None):
        rescueBuilderIfLost(self, logger)

    def updateStatus(self, logger=None):
        updateBuilderStatus(self, logger)


# XXX: It would be *really* nice to run some set of tests against the real
# BuilderSlave and this one to prevent interface skew.
class OkSlave:
    """An idle mock slave that prints information about itself.

    The architecture tag can be customised during initialisation."""

    def __init__(self, arch_tag=I386_ARCHITECTURE_NAME):
        self.call_log = []
        self.arch_tag = arch_tag

    def status(self):
        return ('BuilderStatus.IDLE', '')

    def ensurepresent(self, sha1, url, user=None, password=None):
        self.call_log.append(('ensurepresent', url, user, password))
        return defer.succeed((True, None))

    def build(self, buildid, buildtype, chroot, filemap, args):
        self.call_log.append(('build', buildid, buildtype, chroot, filemap, args))
        info = 'OkSlave BUILDING'
        return ('BuildStatus.Building', info)

    def echo(self, *args):
        self.call_log.append(('echo',) + args)
        return args

    def clean(self):
        self.call_log.append('clean')

    def abort(self):
        self.call_log.append('abort')

    def info(self):
        self.call_log.append('info')
        return ('1.0', self.arch_tag, 'debian')

    def sendFileToSlave(self, sha1, url, username="", password=""):
        self.call_log.append('sendFileToSlave')
        d = self.ensurepresent(sha1, url, username, password)
        def check_present((present, info)):
            if not present:
                raise CannotFetchFile(url, info)
        return d.addCallback(check_present)

    def cacheFile(self, logger, libraryfilealias):
        self.call_log.append('cacheFile')
        return self.sendFileToSlave(
            libraryfilealias.content.sha1, libraryfilealias.http_url)


class BuildingSlave(OkSlave):
    """A mock slave that looks like it's currently building."""

    def __init__(self, build_id='1-1'):
        super(BuildingSlave, self).__init__()
        self.build_id = build_id

    def status(self):
        self.call_log.append('status')
        buildlog = xmlrpclib.Binary("This is a build log")
        return ('BuilderStatus.BUILDING', self.build_id, buildlog)

    def getFile(self, sum):
        self.call_log.append('getFile')
        if sum == "buildlog":
            s = StringIO("This is a build log")
            s.headers = {'content-length': 19}
            return s


class WaitingSlave(OkSlave):
    """A mock slave that looks like it's currently waiting."""

    def __init__(self, state='BuildStatus.OK', dependencies=None,
                 build_id='1-1'):
        super(WaitingSlave, self).__init__()
        self.state = state
        self.dependencies = dependencies
        self.build_id = build_id

        # By default, the slave only has a buildlog, but callsites
        # can update this list as needed.
        self.valid_file_hashes = ['buildlog']

    def status(self):
        self.call_log.append('status')
        return ('BuilderStatus.WAITING', self.state, self.build_id, {},
                self.dependencies)

    def getFile(self, hash):
        self.call_log.append('getFile')
        if hash in self.valid_file_hashes:
            content = "This is a %s" % hash
            s = StringIO(content)
            s.headers = {'content-length': len(content)}
            return s


class AbortingSlave(OkSlave):
    """A mock slave that looks like it's in the process of aborting."""

    def status(self):
        self.call_log.append('status')
        return ('BuilderStatus.ABORTING', '1-1')


class AbortedSlave(OkSlave):
    """A mock slave that looks like it's aborted."""

    def status(self):
        self.call_log.append('status')
        return ('BuilderStatus.ABORTED', '1-1')


class LostBuildingBrokenSlave:
    """A mock slave building bogus Build/BuildQueue IDs that can't be aborted.

    When 'aborted' it raises an xmlrpclib.Fault(8002, 'Could not abort')
    """

    def status(self):
        self.call_log.append('status')
        return ('BuilderStatus.BUILDING', '1000-10000')

    def abort(self):
        self.call_log.append('abort')
        raise xmlrpclib.Fault(8002, "Could not abort")


class BrokenSlave:
    """A mock slave that reports that it is broken."""

    def status(self):
        self.call_log.append('status')
        raise xmlrpclib.Fault(8001, "Broken slave")
