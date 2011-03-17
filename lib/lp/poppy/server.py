# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import asyncore
import tempfile
from time import time

from zope.server.ftp.server import (
    FTPServerChannel,
    STORChannel as OriginalSTORChannel,
    )
from zope.server.serverbase import ServerBase
from zope.server.taskthreads import ThreadedTaskDispatcher

from lp.poppy.filesystem import UploadFileSystem


class Channel(FTPServerChannel):

    def __init__(self, server, conn, addr, adj=None):
        # Work around a zope3 bug where the status messages dict is copied by
        # reference, not by value.
        self.status_messages = dict(self.status_messages)
        self.status_messages['SERVER_READY'] = (
            '220 %s Canonical FTP server ready.')

        FTPServerChannel.__init__(self, server, conn, addr, adj=None)
        self.peername = self.socket.getpeername()
        self.uploadfilesystem, self.fsroot = server.newClient(self)
        self.hook = server.auth_verify_hook

    def close(self):
        FTPServerChannel.close(self)
        self.server.clientFinished(self)

    def _getFileSystem(self):
        return self.uploadfilesystem

    def received(self, data):
        # XXX Steve Alexander 2005-01-18
        #     This is a work-around for a bug in Zope 3's ServerChannelBase
        #     that it doesn't update self.last_activity.
        #     This method can be removed once Zope3 is fixed, and we're using
        #     that code.
        #     http://collector.zope.org/Zope3-dev/350
        self.record_activity()
        FTPServerChannel.received(self, data)

    def record_activity(self):
        self.last_activity = time()

    def cmd_pass(self, args):
        'See IFTPCommandHandler'
        self.authenticated = 0
        password = args
        credentials = (self.username, password)
        okay = True
        if self.hook:
            try:
                if not self.hook(self.fsroot, self.username, password):
                    okay = False
            except:
                okay = False
        if not okay:
            self.reply('LOGIN_MISMATCH')
            self.close_when_done()
        else:
            self.credentials = credentials
            self.authenticated = 1
            self.reply('LOGIN_SUCCESS')

    def cmd_stor(self, args, write_mode='w'):
        'See IFTPCommandHandler'
        if not args:
            self.reply('ERR_ARGS')
            return
        path = self._generatePath(args)

        start = 0
        if self.restart_position:
            self.start = self.restart_position
        mode = write_mode + self.type_mode_map[self.transfer_mode]

        if not self._getFileSystem().writable(path):
            self.reply('ERR_OPEN_WRITE', "Can't write file")
            return

        cdc = STORChannel(self, (path, mode, start))
        self.syncConnectData(cdc)
        self.reply('OPEN_CONN', (self.type_map[self.transfer_mode], path))

    def cmd_cwd(self, args):
        """Permissive 'cwd', creates any target directories requested.

        It relies on the filesystem layer to create directories recursivelly.
        """
        path = self._generatePath(args)
        if not self._getFileSystem().type(path) == 'd':
            self._getFileSystem().mkdir(path)
        self.cwd = path
        self.reply('SUCCESS_250', 'CWD')


class STORChannel(OriginalSTORChannel):

    def received (self, data):
        if data:
            self.inbuf.append(data)
            self.control_channel.record_activity()
            # This is the point at which some data for an upload has been
            # received by the server from a client.


class Server(ServerBase):

    channel_class = Channel

    def __init__(self, ip, port,
                 new_client_hook, client_done_hook, auth_verify_hook,
                 *args, **kw):
        ServerBase.__init__(self, ip, port, *args, **kw)
        self.new_client_hook = new_client_hook
        self.client_done_hook = client_done_hook
        self.auth_verify_hook = auth_verify_hook

    def newClient(self, channel):
        fsroot = tempfile.mkdtemp("-poppy")
        uploadfilesystem = UploadFileSystem(fsroot)
        clienthost, clientport = channel.peername
        try:
            self.new_client_hook(fsroot, clienthost, clientport)
        except Exception:
            # Almost bare except, result logged, to keep server running.
            self.logger.exception("Exception during new client hook")
        return uploadfilesystem, fsroot

    def clientFinished(self, channel):
        clienthost, clientport = channel.peername
        try:
            self.client_done_hook(channel.fsroot, clienthost, clientport)
        except Exception:
            # Almost bare except, result logged, to keep server running.
            self.logger.exception("Exception during client done hook")


def run_server(host, port, ident, numthreads,
               new_client_hook, client_done_hook, auth_verify_hook=None):
    task_dispatcher = ThreadedTaskDispatcher()
    task_dispatcher.setThreadCount(numthreads)
    server = Server(host, port,
                    new_client_hook, client_done_hook, auth_verify_hook,
                    task_dispatcher=task_dispatcher)
    server.SERVER_IDENT = ident
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        # Exit without spewing an exception.
        pass
