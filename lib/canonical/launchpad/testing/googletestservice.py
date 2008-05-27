#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
"""
This script runs a simple HTTP server. The server returns XML files
when given certain user-configurable URLs.
"""


from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from canonical.config import config
from canonical.launchpad.webapp.url import urlsplit
from canonical.pidfile import make_pidfile
import subprocess
import os
import time
import socket
import logging


# Set up basic logging.
log = logging.getLogger(__name__)

# The default service name, used by the Launchpad service framework.
service_name = 'google-webservice'


class GoogleRequestHandler(BaseHTTPRequestHandler):
    """Return an XML file depending on the requested URL."""

    default_content_type = 'text/xml; charset=UTF-8'

    def do_GET(self):
        """See BaseHTTPRequestHandler in the Python Standard Library."""
        urlmap = url_to_xml_map()
        if self.path in urlmap:
            self.return_file(urlmap[self.path])
        else:
            # Return our default route.
            self.return_file(urlmap['*'])

    def return_file(self, filename):
        """Return a HTTP response with 'filename' for content.

        :param filename: The file name to find in the canned-data
            storage location.
        """
        self.send_response(200)
        self.send_header('Content-Type', self.default_content_type)
        self.end_headers()

        content_dir = config.google_test_service.canned_response_directory
        filepath = os.path.join(content_dir, filename)
        content_body = file(filepath).read()
        self.wfile.write(content_body)

    def log_message(self, format, *args):
        """See `BaseHTTPRequestHandler.log_message()`."""
        # Substitute the base class's logger with the Python Standard
        # Library logger.
        message = ("%s - - [%s] %s" %
                   (self.address_string(),
                    self.log_date_time_string(),
                    format%args))
        log.info(message)


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


def get_service_endpoint():
    """Return the host and port that the service is running on."""
    return hostpair(config.google.site)


def service_is_available(timeout=2.0):
    """Return True if the service is up and running.

    :param timeout: BLOCK execution for at most 'timeout' seconds
        before returning False.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout) # Block for 'timeout' seconds.
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


def wait_for_service(timeout=10.0):
    """Poll the service and BLOCK until we can connect to it.

    :param timeout: The socket should timeout after this many seconds.
        Refer to the socket module documentation in the Standard Library
        for possible timeout values.
    """
    host, port = get_service_endpoint()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout) # Block for at most X seconds.

    start = time.time()  # Record when we started polling.
    try:
        while True:
            try:
                sock.connect((host, port))
            except socket.error, err:
                elapsed = (time.time() - start)
                if elapsed > timeout:
                    raise RuntimeError("Socket poll time exceeded.")
            else:
                break
    finally:
        sock.close()  # Clean up.


def hostpair(url):
    """Parse the host and port number out of a URL string."""
    parts  = urlsplit(url)
    host, port = parts[1].split(':')
    port = int(port)
    return (host, port)


def start_as_process():
    """Run this file as a stand-alone Python script.

    Returns a subprocess.Popen object. (See the `subprocess` module in
    the Python Standard Library for details.)
    """
    script = __file__
    if not script.endswith('.py'):
        # Make sure we run the .py file, not the .pyc.
        head, _ = os.path.splitext(script)
        script = head + '.py'
    return subprocess.Popen(script)


def main():
    """Run the HTTP server."""
    # Redirect our service output to a log file.
    # pylint: disable-msg=W0602
    global log
    filelog = logging.FileHandler(config.google_test_service.log)
    log.addHandler(filelog)
    log.setLevel(logging.DEBUG)

    # To support service shutdown we need to create a PID file that is
    # understood by the Launchpad services framework.
    global service_name
    make_pidfile(service_name)

    host, port = get_service_endpoint()
    server = HTTPServer((host, port), GoogleRequestHandler)

    log.info("Starting HTTP Google webservice server on port %s", port)
    server.serve_forever()


if __name__ == '__main__':
    main()
