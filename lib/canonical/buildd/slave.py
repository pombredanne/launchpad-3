# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave implementation

from twisted.web import xmlrpc
import xmlrpclib
from os.path import isdir, exists
import sha

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
        if not isdir(self._cachepath):
            raise ValueError, "FileCache path is not a dir"
        
    def arch(self):
        return self._config.get("slave","architecturetag")

    def status(self):
        return self._status

    def have(self, sha1sum):
        return exists("%s/%s" % (self._cachepath, sha1sum))

    def give(self, content):
        sha1sum = sha.sha(content).hexdigest()
        if self.have(sha1sum): return sha1sum
        f = open("%s/%s" % (self._cachepath, sha1sum), "w")
        f.write(content)
        f.close()
        return sha1sum

    def want(self, sha1sum):
        if not self.have(sha1sum):
            raise ValueError, "Unknown SHA1sum %s" % sha1sum
        f = open("%s/%s" % (self._cachepath, sha1sum), "r")
        c = f.read()
        f.close()
        return c

    def abort(self):
        pass

    def clean(self):
        raise NotImplementedError
    

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
        
        print "Initialised"

    def xmlrpc_echo(self, *args):
        return args

    def xmlrpc_info(self):
        # Return the protocol version and the methods supported
        return self.protocolversion, self.methods, self.slave.arch()

    def xmlrpc_status(self):
        status = self.slave.status()
        if status == BuildDSlave.IDLE:
            return status
        if status == BuildDSlave.BUILDING:
            return status, self.slave.buildid(), self.slave.logtail()
        if status == BuildDSlave.WAITING:
            buildstatus = self.slave.buildstatus()
            if buildstatus == BuildDSlave.OK or \
                   builddstatus == BuildDSlave.PACKAGEFAIL or \
                   builddstatus == BuildDSlave.DEPFAIL:
                return status, buildstatus, self.buildid(), \
                       self.slave.waitingfiles()
            return status, buildstatus, self.buildid()
        if status == BuildDSlave.ABORTED:
            return status, self.buildid()
        # Some issue
        raise ValueError, "Unknown status"
    
    def xmlrpc_have(self, sha1sum):
        return self.slave.have(sha1sum)

    def xmlrpc_give(self, content):
        return self.slave.give(content)
    
    def xmlrpc_want(self, sha1sum):
        return self.slave.want(sha1sum)

    def xmlrpc_abort(self):
        self.slave.abort()
        return BuildDSlave.ABORTED

    def xmlrpc_clean(self):
        self.slave.clean()
        return BuildDSlave.IDLE

    
    
