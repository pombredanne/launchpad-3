# arch-tag: 9493de28-0c03-485f-a77c-85e674c852dc
# (c) 2004  Canonical Software Ltd    
"""Monkey-patch to make popen2.popen2 robust against EINTR (i.e. interrupted
system calls due to signals.

Usage:
    import eintr_hack
    eintr_hack.install()
    # Now use popen2 as normal
"""

import sys
import errno

class EINTR_proofer(object):

    def __init__(self, fd):
        self._fd = fd
        
    def __getattr__(self, name):
        # Delegate most stuff to the read file
        return getattr(self._fd, name)

    def __iter__(self):
        # __iter__ is a magic method, so we need to delegate it explicitly
        # (__getattr__ isn't enough)
        return self

    def read(self, count=None):
        while True:
            try:
                if count:
                    return self._fd.read(count)
                else:
                    return self._fd.read()
            except (OSError, IOError), e:
                if e.errno == errno.EINTR:
                    continue
                raise

    def write(self, bytes=None):
        while True:
            try:
                return self._fd.write(bytes)
            except (OSError, IOError), e:
                if e.errno == errno.EINTR:
                    continue
                raise

    def next(self):
        # For __iter__
        while True:
            try:
                return self._fd.next()
            except (OSError, IOError), e:
                if e.errno == errno.EINTR:
                    continue
                raise


def wrapper(fd):
    """Wrap fd, unless it was created from within Twisted."""
    caller = sys._getframe()
    if caller.f_globals.get('__name__').startswith('twisted.'):
        return fd
    return EINTR_proofer(fd)

def install_on_popen2():
    import popen2
    if getattr(popen2, '__has_eintr_hack', False):
        return
    origpp2 = popen2.popen2
    def _popen2(*args, **kwargs):
        print 'Intercepted popen2'
        r, w = origpp2(*args, **kwargs)
        return wrapper(r), wrapper(w)
    popen2.popen2 = _popen2    
    popen2.__has_eintr_hack = True

def install_on_os():
    import os
    if getattr(os, '__has_eintr_hack', False):
        return
    origp = os.popen
    def _popen(*args, **kwargs):
        print 'Intercepted popen'
        p = origp(*args, **kwargs)
        return wrapper(p)
    os.popen = _popen
    origfdo = os.fdopen
    def _fdopen(*args, **kwargs):
        print 'Intercepted fdopen'
        fd = origfdo(*args, **kwargs)
        return wrapper(fd)
    os.fdopen = _fdopen
    os.__has_eintr_hack = True


def install():
    install_on_popen2()
    install_on_os()
