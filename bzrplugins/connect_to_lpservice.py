#!/usr/bin/env python
"""Script to ask lp-service to fork and connect.

Meant to be equivalent to 'bzr lp-serve --inet' only connecting to the service
to handle the request.
"""

import socket
import sys

# This is done as a simple script so that startup time can be kept low, only
# having a minimal set of dependencies.

class TrivialForwarder(object):
    """Forward requests from stdin/out/err to an appropriate pipe."""

    _timeout = 10000
    _buf_size = 8192

    def __init__(self):
        self.poller = select.poll()

        self.in_to_out = {}
        self.inout_to_buffer = {}

    def add_fifo_to_fid(self, fifo_path, fid):
        """Read from fifo, write to fid"""
        buf = []
        # out from the child gets mapped back to our out, so we read from
        # the child, and write to stdout
        fd_child = os.open(fifo_path,
            os.O_RDONLY | osutils.O_BINARY | os.O_NONBLOCK)
        self.in_to_out[fd_child] = fid
        self.poller.register(fd_child, select.POLLIN)
        self.inout_to_buffer[fid] = buf
        self.inout_to_buffer[fd_child] = buf

    def add_fid_to_fifo(self, fid, fifo_path):
        """Read from fid, write to fifo"""
        buf = []
        # We don't use O_NONBLOCK, because otherwise it raises an error if
        # the write side isn't open yet, however it does mean we definitely
        # need to open it *last*
        fd_child = os.open(in_path, os.O_WRONLY | osutils.O_BINARY)
        self.in_to_out[fid] = fd_child
        self.poller.register(fid, select.POLLIN)
        self.inout_to_buffer[fid] = buf
        self.inout_to_buffer[fd_child] = buf

    def run(self):
        should_close = set()
        while True:
            events = self.poller.poll(self._timeout) # TIMEOUT?
            if not events:
                ## self.log('** timeout\n')
                # TODO: check if all buffers are indicated 'closed' so we
                #       should exit
                continue
            for fd, event in events:
                ## self.log('event: %s %s  ' % (fd, event))
                if event & select.POLLIN:
                    # Register the output buffer, buffer a bit, and wait for
                    # the output to be available
                    buf = inout_to_buffer[fd]
                    # TODO: We could set a maximum size for buf, and if we go
                    #       beyond that, we stop reading
                    # n_buffered = sum(map(len, buf))
                    thebytes = os.read(fd, self._buf_size)
                    buf.append(thebytes)
                    out_fd = in_to_out[fd]
                    ## self.log('read %d => %d register %d\n'
                    ##          % (len(thebytes), sum(map(len, buf)),
                    ##             out_fd))
                    # Let the poller know that we need to do non-blocking output
                    # We always re-register, we could know that it is already
                    # active
                    if not thebytes:
                        # Input without content, treat this as a close request
                        should_close.add(out_fd)
                        poller.unregister(fd)
                        os.close(fd)
                        ## self.log('no bytes closed closed, closing %d\n'
                        ##          % (out_fd,))
                    poller.register(out_fd, select.POLLOUT)
                elif event & select.POLLOUT:
                    # We can write some bytes without blocking, do so
                    buf = inout_to_buffer[fd]
                    if not buf:
                        # the buffer is now empty, we have written everything
                        # so unregister this buffer so we don't keep polling
                        # for the ability to write without blocking
                        ## self.log('unregistered\n')
                        poller.unregister(fd)
                        # Check to see if the input has been closed, and close
                        # if true
                        if fd in should_close:
                            ## self.log('%d closed\n' % (fd,))
                            os.close(fd)
                        continue
                    thebytes = ''.join(buf)
                    n_written = os.write(fd, thebytes)
                    thebytes = thebytes[n_written:]
                    ## self.log('\n  wrote %d => %d remain\n'
                    ##          % (n_written, len(thebytes)))
                    if thebytes:
                        buf[:] = [thebytes]
                    else:
                        del buf[:]
                        # We *could* unregister the output here, but I have the
                        # feeling waiting for another poll loop will be better
                        # because it will avoid looping, oh we have bytes,
                        # register, loop, find bytes, write them, unregister,
                        # loop, find more bytes, register, loop, etc.
                        # I don't know for sure, but I think this gives us at
                        # least a chance to have more bytes to write before we
                        # unregister
                elif event & select.POLLHUP:
                    # The connection hung up, I'm assuming these only occur on
                    # the inputs for now..., but carry across the action.
                    # Importantly, we don't close the out_fd yet, because we
                    # want to flush the buffer first
                    poller.unregister(fd)
                    out_fd = in_to_out[fd]
                    should_close.add(out_fd)
                    ## self.log('closed, closing %d\n'
                    ##          % (out_fd,))


def _get_host_and_port(port):
    host = None
    if port is not None:
        if ':' in port:
            host, port = port.rsplit(':', 1)
        port = int(port)
    return host, port

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 4156


def main(args):
    import optparse
    p = optparse.OptionParser('%prog [options] userid')
    p.add_option('--port',
        help='The [host:]portnumber where the service is running')
    opts, args = p.parse_args()
    if len(args) != 1:
        p.print_usage()
        return 1
    userid = int(args[0])
    host, port = _get_host_and_port(opts.port)
    if host is None:
        host = DEFAULT_HOST
    if port is None:
        port = DEFAULT_PORT
    path = _request_fork(host, port, userid)
    _connect_to_fifos(path)


def _request_fork(host, port, user_id):
    """Ask the server to fork, and find out the new process's disk path."""
    # Connect to the service, and request a new connection.
    addrs = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
        socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
    (family, socktype, proto, canonname, sockaddr) = addrs[0]
    client_sock = socket.socket(family, socktype, proto)
    try:
        client_sock.connect(sockaddr)
        client_sock.sendall('fork %d\n' % (user_id,))
        response = client_sock.recv(1024)
    except socket.error, e:
        raise RuntimeError('Failed to connect: %s' % (e,))
    if response.startswith('FAILURE'):
        raise RuntimeError('Server rejected with: %s' % (response,))
    # we got a valid path back, so lets return it
    return response.strip()


def _connect_to_fifos(path):
    stdin_path = os.path.join(path, 'stdin')
    stdout_path = os.path.join(path, 'stdout')
    stderr_path = os.path.join(path, 'stderr')
    forwarder = TrivialForwarder()
    forwarder.add_fifo_to_fid(stdout_path, sys.stdout)
    forwarder.add_fifo_to_fid(stderr_path, sys.stderr)
    forwarder.add_fid_to_fifo(sys.stdout, stdout_path)
    forwarder.run()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
