# Copyright 2004 Canonical Ltd.  All rights reserved.
#

# XXX: Write doctests for this network protocol in the style of page tests.
#       - Andrew Bennetts, 2005-03-24.

from twisted.internet import protocol
from twisted.internet.threads import deferToThread
from twisted.protocols import basic
from twisted.python import log
from canonical.lp import initZopeless


class ProtocolViolation(Exception):
    def __init__(self, msg):
        self.msg = msg


class FileUploadProtocol(basic.LineReceiver):
    """Simple HTTP-like protocol for file uploads.

    A client sends an upload with a request like::

        STORE 10000 foo.txt
        Optional-Header: value
        Optional-Header: value
        
        <....10000 bytes....>
    
    And this server will respond with::

        200 1234/5678
    
    Where "1234" is the file id in our system, and "5678" is file alias id.

    Recognised headers are:
      :Content-Type: a mime-type to associate with the file
      :File-Content-ID: if specified, the integer file id for this file.  If not
        specified, the server will generate one.
      :File-Alias-ID: if specified, the integer file alias id for this file.  If
        not specified, the server will generate one.

    The File-Content-ID and File-Alias-ID headers are also described in
    https://wiki.launchpad.canonical.com/LibrarianTransactions.
    
    Unrecognised headers will be ignored.

    If something goes wrong, the server will reply with a 400 (bad request) or
    500 (internal server error) response codes instead, and an appropriate
    message.

    Once the server has replied, the client may re-use the connection as if it
    were just established to start a new upload.
    """
    
    delimiter = '\r\n'  # same as HTTP
    state = 'command'
    
    def lineReceived(self, line):
        try:
            getattr(self, 'line_' + self.state, self.badLine)(line)
        except ProtocolViolation, e:
            self.sendLine('400 ' + e.msg)
            self.transport.loseConnection()
        except:
            self.error()
    
    def error(self, failure=None):
        log.msg('Uncaught exception in FileUploadProtocol:')
        if failure is not None:
            log.err(failure)
        else:
            log.err()
        self.sendLine('500 Internal server error')
        self.transport.loseConnection()
    
    def badLine(self, line):
        raise ProtocolViolation('Unexpected message from client: ' + line)

    def line_command(self, line):
        try:
            command, args = line.split(None, 1)
        except ValueError:
            raise ProtocolViolation('Bad command: ' + line)
        
        bad = lambda args: self.badCommand(line)
        getattr(self, 'command_' + command.upper(), bad)(args)
                
    def line_header(self, line):
        # Blank line signals the end of the headers
        if line == '':
            # If File-Content-ID was specified, File-Alias-ID must be too, and
            # vice-versa.
            contentID = self.newFile.contentID
            aliasID = self.newFile.aliasID
            if ((contentID is not None and aliasID is None) or
                (aliasID is not None and contentID is None)):
                    raise ProtocolViolation(
                        "File-Content-ID and File-Alias-ID must both be "
                        "specified"
                    )
            
            # If that's ok, we're ready to receive the file.
            self.state = 'file'
            self.setRawMode()
            return

        # Simple RFC 822-ish header parsing
        try:
            name, value = line.split(':', 2)
        except ValueError:
            raise ProtocolViolation('Invalid header: ' + line)

        ignore = lambda value: None
        value = value.strip()
        name = name.lower().replace('-', '_')
        getattr(self, 'header_' + name, ignore)(value)
                
    def badCommand(self, line):
        raise ProtocolViolation('Unknown command: ' + line)

    def command_STORE(self, args):
        try:
            size, name = args.split(None, 2)
            try:
                name = name.decode('utf-8')
            except:
                raise ProtocolViolation(
                    "STORE command expects the filename to be in UTF-8")
            size = int(size)
        except ValueError:
            raise ProtocolViolation(
                    "STORE command expects a size and file name")
        fileLibrary = self.factory.fileLibrary
        self.newFile = fileLibrary.startAddFile(name, size)
        self.bytesLeft = size
        self.state = 'header'

    def header_content_type(self, value):
        self.newFile.mimetype = value

    def header_sha1_digest(self, value):
        self.newFile.srcDigest = value

    def header_file_content_id(self, value):
        try:
            self.newFile.contentID = int(value)
        except ValueError:
            raise ProtocolViolation("Invalid File-Content-ID: " + value)

    def header_file_alias_id(self, value):
        try:
            self.newFile.aliasID = int(value)
        except ValueError:
            raise ProtocolViolation("Invalid File-Alias-ID: " + value)

    def rawDataReceived(self, data):
        realdata, rest = data[:self.bytesLeft], data[self.bytesLeft:]
        self.bytesLeft -= len(realdata)
        self.newFile.append(realdata)

        if self.bytesLeft == 0:
            # Store file
            deferred = deferToThread(self.newFile.store)
            def _sendID((fileID, aliasID)):
                # Send ID to client
                if self.newFile.contentID is None:
                    # Respond with deprecated server-generated IDs
                    self.sendLine('200 %s/%s' % (fileID, aliasID))
                else:
                    self.sendLine('200')
            deferred.addCallback(_sendID)
            deferred.addErrback(self.error)

            # Treat remaining bytes (if any) as a new command
            self.state = 'command'
            self.setLineMode(rest)


class FileUploadFactory(protocol.Factory):
    protocol = FileUploadProtocol
    def __init__(self, fileLibrary):
        self.fileLibrary = fileLibrary


if __name__ == '__main__':
    import os, sys
    from twisted.internet import reactor
    from twisted.python import log
    log.startLogging(sys.stdout)
    from canonical.librarian import db, storage
    from canonical.arch.sqlbase import SQLBase
    initZopeless()
    
    try:
        os.mkdir('/tmp/fatsam')
    except:
        pass
    f = FileUploadFactory(storage.LibrarianStorage('/tmp/fatsam', db.Library()))
    reactor.listenTCP(9090, f)
    reactor.run()
