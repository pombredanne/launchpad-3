# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation

import xmlrpclib
from os.path import isdir, exists
from os import mkdir, symlink, kill, environ, remove
from signal import SIGKILL
import sha
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.web import xmlrpc

class RunCapture(protocol.ProcessProtocol):
    """Run a command and capture its output to a slave's log"""

    def outReceived(self, data):
        self.slave.log(data)

    def processEnded(self, statusobject):
        self.notify(statusobject.value.exitCode)

class BuildManager(object):
    """Build Daemon slave build manager abstract parent
    """

    def __init__(self, slave, buildid):
        object.__init__(self)
        self._buildid = buildid
        self._slave = slave
        self._unpackpath = slave._config.get("allmanagers", "unpackpath")
        self._cleanpath = slave._config.get("allmanagers", "cleanpath")
        self._mountpath = slave._config.get("allmanagers", "mountpath")
        self._umountpath = slave._config.get("allmanagers", "umountpath")

    def runSubProcess(self, command, args):
        self._subprocess = RunCapture()
        self._subprocess.slave = self._slave
        self._subprocess.notify = self.iterate
        self._slave.log("RUN: %s %r\n" % (command,args))
        reactor.spawnProcess(self._subprocess,
                             command,
                             args,
                             environ,
                             environ["HOME"],
                             None,
                             None,
                             False)

    def _unpackChroot(self, chroottarfile):
        self.runSubProcess(self._unpackpath,
                           [ "unpack-chroot", self._buildid, chroottarfile ])

    def doCleanup(self):
        self.runSubProcess( self._cleanpath,
                            ["remove-build", self._buildid] )

    def doMounting(self):
        self.runSubProcess( self._mountpath,
                            ["mount-chroot", self._buildid] )
        
    def doUnmounting(self):
        self.runSubProcess( self._umountpath,
                            ["umount-chroot", self._buildid] )

    def symlink(self, old, new):
        print "create symlink called %s pointing to existing %s" % (new,old)
        symlink(old,new)
        
    def initiate(self, files, chroot):
        """Initiate a build given the input files"""
        mkdir("%s/build-%s" % (environ["HOME"], self._buildid))
        for f in files:
            self.symlink( self._slave.cachePath(files[f]), "%s/build-%s/%s" % (environ["HOME"], self._buildid, f) )
        self._unpackChroot(self._slave.cachePath(chroot))

    def iterate(self, success):
        raise UnimplementedError

    def abort(self):
        if not self.alreadyfailed:
            self.alreadyfailed = True
        kill(self.subprocess.transport.pid, SIGKILL)

class BuildDSlave(object):
    """Build Daemon slave
    """

    IDLE = "BuilddStatus.IDLE"
    BUILDING = "BuilddStatus.BUILDING"
    WAITING = "BuilddStatus.WAITING"
    ABORTED = "BuilddStatus.ABORTED"

    OK = "BuilddStatus.OK"
    DEPFAIL = "BuilddStatus.DEPFAIL"
    PACKAGEFAIL = "BuilddStatus.PACKAGEFAIL"
    CHROOTFAIL = "BuilddStatus.CHROOTFAIL"
    BUILDERFAIL = "BuilddStatus.BUILDERFAIL"
    
    def __init__(self, config):
        object.__init__(self)
        self._config = config
        self._status = BuildDSlave.IDLE
        self._cachepath = self._config.get("slave","filecache")
        self._buildstatus = BuildDSlave.OK
        self._waiting = {}
        
        if not isdir(self._cachepath):
            raise ValueError, "FileCache path is not a dir"
        
    def arch(self):
        return self._config.get("slave","architecturetag")

    def status(self):
        return self._status

    def buildstatus(self):
        return self._buildstatus

    def waitingfiles(self, filemap = None):
        if filemap is not None:
            self._waiting = filemap
        return self._waiting

    def cachePath(self, file):
        return "%s/%s" % (self._cachepath, file)

    def have(self, sha1sum):
        # XXX: dsilvers: 2005/01/21: We could go to a librarian here
        return exists(self.cachePath(sha1sum))

    def give(self, content):
        sha1sum = sha.sha(content).hexdigest()
        if self.have(sha1sum): return sha1sum
        f = open(self.cachePath(sha1sum), "w")
        f.write(content)
        f.close()
        return sha1sum

    def want(self, sha1sum):
        if not self.have(sha1sum):
            raise ValueError, "Unknown SHA1sum %s" % sha1sum
        f = open(self.cachePath(sha1sum), "r")
        c = f.read()
        f.close()
        return c

    def abort(self):
        # XXX: dsilvers: 2005/01/21: Current abort mechanism doesn't wait
        # for abort to complete. This is potentially an issue in a heavy
        # load situation
        if self._status != BuildDSlave.BUILDING:
            raise ValueError, "Slave is not BUILDING when asked to abort"
        self.manager.abort()
        self._status = BuildDSlave.ABORTED

    def clean(self):
        # Delete everything waiting and reset internal state
        if self._status != BuildDSlave.WAITING:
            raise ValueError, "Slave is not WAITING when asked to clean"
        for f in self._waiting:
            remove(self.cachePath(self._waiting[f]))
        self._status = BuildDSlave.IDLE
        self._log = ""
        self._waiting = {}
        self.manager = None
        self._buildstatus = BuildDSlave.OK

    def emptyLog(self):
        self._log = ""

    def log(self, data):
        # XXX: dsilvers: 2005/01/21: Largest build log I've seen is 50 megs
        # but we might have to consider using a disk file if that gets worse
        self._log += data
        if data.endswith("\n"):
            data = data[:-1]
        print "Build log: " + data

    def logtail(self, amount):
        if amount == -1:
            return self._log
        if amount > len(self._log):
            amount = len(self._log)
        ret = self._log[len(self._log)-amount:]
        return ret[ret.find("\n")+1:]

    def startBuild(self, manager):
        if self._status != BuildDSlave.IDLE:
            raise ValueError, "Slave is not IDLE when asked to start building"
        self.manager = manager
        self._status = BuildDSlave.BUILDING

    def builderFail(self):
        if self._status != BuildDSlave.BUILDING:
            raise ValueError, "Slave is not BUILDING when set to BUILDERFAIL"
        self._status = BuildDSlave.WAITING
        self._buildstatus = BuildDSlave.BUILDERFAIL

    def buildFail(self):
        if self._status != BuildDSlave.BUILDING:
            raise ValueError, "Slave is not BUILDING when set to BUILDFAIL"
        self._status = BuildDSlave.WAITING
        self._buildstatus = BuildDSlave.PACKAGEFAIL

    def buildComplete(self):
        if self._status != BuildDSlave.BUILDING:
            raise ValueError, "Slave is not BUILDING when told build is complete"
        self._status = BuildDSlave.WAITING
        self._buildstatus = BuildDSlave.OK
        

class XMLRPCBuildDSlave(xmlrpc.XMLRPC):
    """XMLRPC build daemon slave management interface

    """

    def __init__(self, config):
        xmlrpc.XMLRPC.__init__(self)
        self.protocolversion = 1
        self.methods = []
        for k in dir(self):
            if k.startswith("xmlrpc_"):
                self.methods.append(k[7:])
        self.slave = BuildDSlave(config)
        self._builders = {}
        
        print "Initialised"

    def registerBuilder(self, builderclass, buildertag):
        self._builders[buildertag] = builderclass

    def xmlrpc_echo(self, *args):
        return args

    def xmlrpc_info(self):
        # Return the protocol version and the methods supported
        return self.protocolversion, self.methods, self.slave.arch(), self._builders.keys()

    def xmlrpc_status(self):
        status = self.slave.status()
        if status == BuildDSlave.IDLE:
            return status
        if status == BuildDSlave.BUILDING:
            return status, self.buildid, self.slave.logtail(1024)
        if status == BuildDSlave.WAITING:
            buildstatus = self.slave.buildstatus()
            if buildstatus == BuildDSlave.OK or \
                   buildstatus == BuildDSlave.PACKAGEFAIL or \
                   buildstatus == BuildDSlave.DEPFAIL:
                print status, buildstatus, self.buildid, \
                       self.slave.waitingfiles()
                return status, buildstatus, self.buildid, \
                       self.slave.waitingfiles()
            return status, buildstatus, self.buildid
        if status == BuildDSlave.ABORTED:
            return status, self.buildid
        # Some issue
        raise ValueError, "Unknown status"

    def xmlrpc_fetchlogtail(self, amount):
        return self.slave.logtail(amount)
    
    def xmlrpc_doyouhave(self, sha1sum):
        return self.slave.have(sha1sum)

    def xmlrpc_storefile(self, content):
        return self.slave.give(content)
    
    def xmlrpc_fetchfile(self, sha1sum):
        return self.slave.want(sha1sum)

    def xmlrpc_abort(self):
        self.slave.abort()
        return BuildDSlave.ABORTED

    def xmlrpc_clean(self):
        self.slave.clean()
        return BuildDSlave.IDLE

    def xmlrpc_startbuild(self, buildid, filelist, chrootsum, builder):
        if not builder in self._builders:
            return "UNKNOWN-BUILDER"
        if not self.slave.have(chrootsum):
            return "UNKNOWN-SUM", chrootsum
        for f in filelist:
            if not self.slave.have(filelist[f]):
                return "UNKNOWN-SUM", filelist[f]
        if buildid is None or buildid == "" or buildid == 0:
            raise ValueError, buildid
        # builder is available, buildd is non empty,
        # filelist is consistent, chrootsum is available, let's initiate...

        self.buildid = buildid
        
        self.slave.startBuild(self._builders[builder](self.slave, buildid))
        self.slave.manager.initiate(filelist, chrootsum)
        return "BUILDING"
    
