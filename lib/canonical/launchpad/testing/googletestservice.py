#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
"""
This script runs a simple HTTP server. The server returns XML files
when given certain user-configurable URLs.
"""


from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from canonical.config import config
from canonical.launchpad.webapp.url import urlsplit
import subprocess
import os
import time
import socket


class GoogleRequestHandler(BaseHTTPRequestHandler):

    default_content_type = 'text/xml; charset=UTF-8'

    def do_GET(self):
        urlmap = url_to_xml_map()
        if self.path in urlmap:
            self.return_file(urlmap[self.path])
        else:
            # Return our default route.
            self.return_file(urlmap['*'])

    def return_file(self, filename):
        """Return a HTTP response with `filename' for content.

        `filename' is searched for in the default canned-data storage
        location, specified in the service configuration.
        """
        self.send_response(200)
        self.send_header('Content-Type', self.default_content_type)
        self.end_headers()

        content_dir = config.google_test_service.canned_response_directory
        filepath = os.path.join(content_dir, filename)
        content_body = file(filepath).read()
        self.wfile.write(content_body)


def url_to_xml_map():
    """Return our URL-to-XML mapping as a dictionary."""
    mapfile = config.google_test_service.mapfile
    mapping = {}
    for line in file(mapfile):
        if line.startswith('#') or len(line.strip()) == 0:
            # Skip comments and blank lines.
            continue
        url, fname = line.split()
        mapping[url.strip()] = fname.strip()

    return mapping

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
    return hostpair(config.google.site)

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
    server = HTTPServer((host, port), GoogleRequestHandler)

    print "Starting HTTP Google webservice server on port", port
    server.serve_forever()


if __name__ == '__main__':
    main()
