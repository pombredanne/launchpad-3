# Copyright (c) 2005-2006 Canonical Ltd.

"""Helper for test cases that need an http server.

This code is based on the bzr code for doing http tests.
"""

__metaclass__ = type
__all__ = ['BadWebserverPath', 'WebserverHelper']

from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import socket

from importd.tests.helpers import SandboxHelper


class BadWebserverPath(ValueError):
    def __str__(self):
        return 'path %s is not in %s' % self.args


class TestHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class WebserverHelper(SandboxHelper):

    def _http_start(self):
        httpd = HTTPServer(('localhost', 0), TestHTTPRequestHandler)
        host, port = httpd.socket.getsockname()

        self._http_base_url = 'http://localhost:%s/' % port
        self._http_starting.release()
        httpd.socket.settimeout(0.1)

        while self._http_running:
            try:
                httpd.handle_request()
            except socket.timeout:
                pass

    def get_remote_url(self, path):
        import os

        path_parts = path.split(os.path.sep)
        if os.path.isabs(path):
            if path_parts[:len(self._local_path_parts)] != \
                   self._local_path_parts:
                raise BadWebserverPath(path, self.path)
            remote_path = '/'.join(path_parts[len(self._local_path_parts):])
        else:
            remote_path = '/'.join(path_parts)

        self._http_starting.acquire()
        self._http_starting.release()
        return self._http_base_url + remote_path

    def setUp(self):
        SandboxHelper.setUp(self)
        import threading, os
        self._local_path_parts = self.path.split(os.path.sep)
        self._http_starting = threading.Lock()
        self._http_starting.acquire()
        self._http_running = True
        self._http_base_url = None
        self._http_thread = threading.Thread(target=self._http_start)
        self._http_thread.setDaemon(True)
        self._http_thread.start()
        self._http_proxy = os.environ.get("http_proxy")
        if self._http_proxy is not None:
            del os.environ["http_proxy"]

    def tearDown(self):
        self._http_running = False
        self._http_thread.join()
        if self._http_proxy is not None:
            import os
            os.environ["http_proxy"] = self._http_proxy
        SandboxHelper.tearDown(self)
