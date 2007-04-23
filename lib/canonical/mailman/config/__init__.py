# Copyright 2007 Canonical Ltd.  All rights reserved.

"""ZConfig datatypes for <mailman> and <mailman-build> configuration keys."""


import os
import grp
import pwd
import socket


def prefix(value):
    if value:
        return os.path.abspath(value)
    return os.path.abspath(os.path.join('lib', 'mailman'))


def usergroup(value):
    # Make sure the target directories exist and have the correct
    # permissions, otherwise configure will complain.
    if not value:
        user  = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
        return user, group
    return value.split(':', 1)


def hostname(value):
    if value:
        return value
    return socket.getfqdn()
