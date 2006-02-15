# Copyright 2006 Canonical Ltd.  All rights reserved.

import urlparse

from twisted.internet import defer, protocol, reactor
from twisted.web.http import HTTPClient
from twisted.web import error


class ProberProtocol(HTTPClient):
    """Simple HTTP client to probe path existence via HEAD."""

    def connectionMade(self):
        """Simply requests path presence."""
        self.makeRequest()
        
    def makeRequest(self):
        """Request path presence via HTTP/1.1 using HEAD.

        Uses facotry.host and factory.host
        """
        self.sendCommand('HEAD', self.factory.path)
        self.sendHeader('HOST', self.factory.host)
        self.endHeaders()
        
    def lineReceived(self, data):
        """Receive lines from Server and parse them."""
        line = data.strip()
        if line.startswith('HTTP'):
            self.factory.parseResult(line)

    def handleResponse(self, response):
        """Force the connection end anyway."""
        self.transport.loseConnection()


class ProberTimeout(error.Error):
    """The initialized URL did not return at time."""


class ProberFactory(protocol.ClientFactory):
    """Factory using ProberProtocol to probe single URL existence."""
    protocol = ProberProtocol

    def __init__(self, url, timeout=1):
        self.deferred = defer.Deferred()
        self.setTimeout(timeout)
        self.setURL(str(url))
        
    def setTimeout(self, timeout):
        self.timeout = timeout
        self.timeoutCall = reactor.callLater(timeout, self.timeOut)

    def timeOut(self):
        self.deferred.errback(ProberTimeout('TIMEOUT'))

    def _parse(self, url, defaultPort=80):
        parsed = urlparse.urlparse(url)
        scheme = parsed[0]
        path = urlparse.urlunparse(('','') + parsed[2:])
        host, port = parsed[1], defaultPort
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        return scheme, host, port, path

    def setURL(self, url):
        self.url = url
        scheme, host, port, path = self._parse(url)
        if scheme and host:
            self.scheme = scheme
            self.host = host
            self.port = port
        self.path = path

    def buildProtocol(self, addr):
        return protocol.ClientFactory.buildProtocol(self, addr)
    
    def parseResult(self, line):
        if self.timeoutCall.active():
            self.timeoutCall.cancel()
        self.deferred.callback(line)


def returnResult(result, prober):
    return '"%s" -> %s' % (prober.url, result)
    return prober.url

def printResult(result, prober):
    print result
    return prober.url

def printError(reason, prober):
    if reason.type == ProberTimeout:
        print "timeout in %s" % prober.url
    else:
        print "another error in %s: %s" % (prober.url, reason)
    return prober.url

def checkComplete(result, unchecked, prober):
    if len(unchecked):
        unchecked.remove(result)

    if not len(unchecked):
        reactor.callLater(0, finish)

def finish():
    print 'Done'
    reactor.stop()


if __name__ == '__main__':
    
    urls = [
        'http://all.mirrors.com/pub/ubuntu',
        'http://localhost/',
        'http://localhost/index.html',
        'http://localhost/index.php',
        'http://www.terra.com.br/dists/warty',
        'http://locahost/ubuntu/dists/warty',
        'http://www.gwyddion.com/dists/',
        'http://archive.ubuntu.com/ubuntu/dists/breezy/main/source/Sources.gz',
        'http://foo.bar.com/pub/ubuntu',
        ]
    
    unchecked = urls[:]
    index = 0
    
    for url in urls:
        index += 1
        prober = ProberFactory(url)
        prober.deferred.addCallback(returnResult, prober)
        prober.deferred.addCallback(printResult, prober)
        prober.deferred.addErrback(printError, prober)
        prober.deferred.addBoth(checkComplete, unchecked, prober)
        reactor.connectTCP(prober.host, prober.port, prober)
        
    reactor.run()
