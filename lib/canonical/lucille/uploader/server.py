# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import zope.server.ftp.server as ftp
from zope.interface import implements
from zope.server.interfaces.ftp import IFileSystem
from zope.server.interfaces.ftp import IFileSystemAccess

import zope.server.ftp.tests.demofs as demofs
from zope.server.ftp.server import FTPServerChannel
from zope.server.taskthreads import ThreadedTaskDispatcher
import ThreadedAsync
import logging
import os
import sys
from zope.server.serverbase import ServerBase
from canonical.lucille.uploader.filesystem import UploadFileSystem

class Channel(FTPServerChannel):

    jdub_sez = "yo yo pants off"

    def __init__(self, server, conn, addr, adj=None):
        # Work around a zope3 bug where the status messages dict is copied by
        # reference, not by value.
        self.status_messages = dict(self.status_messages)
        self.status_messages['SERVER_READY'] = (
            '220 %%s FTP server (%s) ready.' % self.jdub_sez)

        FTPServerChannel.__init__(self, server, conn, addr, adj=None)
        self.peername = self.socket.getpeername()
        self.uploadfilesystem, self.fsroot = server.newClient(self)

    def close(self):
        FTPServerChannel.close(self)
        self.server.clientFinished(self)

    def _getFileSystem(self):
        return self.uploadfilesystem

    def cmd_pass(self, args):
        'See IFTPCommandHandler'
        self.authenticated = 0
        password = args
        credentials = (self.username, password)
        self.credentials = credentials
        self.authenticated = 1
        self.reply('LOGIN_SUCCESS')


class Server(ServerBase):

    channel_class = Channel

    def __init__(self, ip, port, root, startcount,
                 new_client_hook, client_done_hook,
                 *args, **kw):
        ServerBase.__init__(self, ip, port, *args, **kw)
        self.clientcount = startcount
        self.rootpath = root
        self.new_client_hook = new_client_hook
        self.client_done_hook = client_done_hook

    def newClient(self, channel):
        root = '/'  # sentinel
        while os.path.exists(root):
            self.clientcount += 1
            root = os.path.join(self.rootpath,
                                'upload-%06.f' % self.clientcount)
        os.mkdir(root)
        uploadfilesystem = UploadFileSystem(root)
        clienthost, clientport = channel.peername
        try:
            self.new_client_hook(root, clienthost, clientport)
        except Exception:
            # Almost bare except, result logged, to keep server running.
            self.logger.exception("Exception during new client hook")
        return uploadfilesystem, root

    def clientFinished(self, channel):
        clienthost, clientport = channel.peername
        try:
            self.client_done_hook(channel.fsroot, clienthost, clientport)
        except Exception:
            # Almost bare except, result logged, to keep server running.
            self.logger.exception("Exception during client done hook")


def run_server(rootdir, host, port, ident, numthreads,
               new_client_hook, client_done_hook):
    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(numthreads)
    server = Server(host, port, rootdir, 0,
                    new_client_hook, client_done_hook,
                    task_dispatcher=task_dispatcher)
    server.SERVER_IDENT = ident
    try:
        ThreadedAsync.loop()
    except KeyboardInterrupt:
        # Exit without spewing an exception.
        pass


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print "usage: server.py rootuploaddirectory port"
        return 1
    root, port = args
    host = "127.0.0.1"
    ident = "lucille upload server"
    numthreads = 4

    logger = logging.getLogger('Server')
    hdlr = logging.FileHandler('lucilleupload.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.WARNING)

    def new_client_hook(fsroot, host, port):
        print "new client:", fsroot, host, port

    def client_done_hook(fsroot, host, port):
        print "client done:", fsroot, host, port


    run_server(root, host, int(port), ident, numthreads,
               new_client_hook, client_done_hook)
    return 0

if __name__ == '__main__':
    sys.exit(main())
