#!/usr/bin/env python2.4
# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""
This script runs a simple HTTP server that can simulate a number of
nasty network failures.

It works by POSTing a set of configuration variables to a URL, along
with a representation.

For example, you may post an XML file along with the option
'limit-rate=50'.  Visiting any other URL on the server will return the
XML file at 50 bytes per second.
"""


from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from canonical.config import config
from canonical.launchpad.webapp.url import urlsplit
import subprocess
import os
import time
import socket


class ConfigurableRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.route('GET')

    def do_POST(self):
        self.route('POST')

    def route(self, http_method):
        """Route a HTTP request to the correct resource handler."""
        if self.path.startswith('/configuration'):
            mbase = 'do_configuration_'
        else:
            mbase = 'do_default_'

        method = mbase + http_method
        getattr(self, method)()

    def do_default_GET(self):
        """Handle HTTP GET to an arbitrary resource."""
        self.send_response(405) # HTTP Status 405: Method not allowed.
        self.end_headers()

    def do_default_POST(self):
        """Handle HTTP POST to an abitrary resource."""
        self.send_response(405) # HTTP Status 405: Method not allowed.
        self.end_headers()

    def do_configuration_GET(self):
        """Handle HTTP GET requests to the 'configuration' resource."""
        self.send_response(405) # HTTP Status 405: Method not allowed.
        self.end_headers()

    def do_configuration_POST(self):
        """Handle HTTP POST requests to the 'configuration' resource."""
        self.send_response(405) # HTTP Status 405: Method not allowed.
        self.end_headers()


def start_as_process():
    """Start the script as a stand-alone process."""
    script = __file__
    if not script.endswith('.py'):
        # Make sure we run the .py file, not the .pyc.
        head, _ = os.path.splitext(script)
        script = head + '.py'
    proc = subprocess.Popen(script)

    # Wait for our new service to become available, using a safe
    # technique to do so.
    host, port = get_service_endpoint()
    wait_for_service(host, port)
    return proc

def get_service_endpoint():
    """Return the host and port that the service is running on."""
    return hostpair(config.google_test_service.test_url)

def service_is_available(timeout=10.0):
    """Return True if the service is up and running."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout) # Block for `timeout' seconds.
    host, port = get_service_endpoint()
    try:
        try:
            sock.connect((host, port))
        except socket.error, err:
            return False
        else:
            return True
    finally:
        sock.close() # Clean up.

def wait_for_service(host, port, timeout=2.0):
    """Poll the service and BLOCK until we can connect to it.

    The socket has a default timeout, just in case. See the socket
    module documentation for special timeout values.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout) # Block for at most X seconds.

    # Try to stop polling after X seconds.
    start = time.time()
    try:
        while 1:
            try:
                sock.connect((host, port))
            except socket.error, err:
                elapsed = (time.time() - start) # Convert to seconds.
                if elapsed > timeout:
                    raise RuntimeError("Socket poll time exceeded.")
            else:
                break
    finally:
        sock.close()  # Clean up.

def hostpair(url):
    """Return the host and port for the specified URL."""
    parts  = urlsplit(url)
    host, port = parts[1].split(':')
    port = int(port)
    return (host, port)


def main():
    """Run the HTTP server."""
    host, port = get_service_endpoint()
    server = HTTPServer((host, port), ConfigurableRequestHandler)

    print "Starting HTTP Google webservice server on port", port
    server.serve_forever()


if __name__ == '__main__':
    main()
