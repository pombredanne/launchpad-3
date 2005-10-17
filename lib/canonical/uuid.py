# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Unique identifier generators"""

__metaclass__ = type

__all__ = ['generate_uuid']

import time, random, subprocess, thread, sha

from canonical.base import base

_machine_secret = None

def generate_uuid():
    """A UUID generator generating (probably) unique identifiers, compressed
    into a string containing less than 27 characters in the set [0-9a-zA-Z]

    The uuids are generated using the system clock, the thread identifier,
    the machines MAC and IP addresses and Pythons random number generator.

    >>> generate_uuid() == generate_uuid()
    False

    Generate 1000 uuids, ensuring they are unique, short and contain
    only documented characters.

    >>> import re
    >>> uuids = []
    >>> for loop in range(0, 1000):
    ...     uuid = generate_uuid()
    ...     if uuid in uuids:
    ...         print 'Non unique uuid %s generated' % uuid
    ...         break
    ...     if re.search("^[0-9a-zA-Z]{1,27}$", uuid) is None:
    ...         print 'Invalid uuid %s generated' % uuid
    ...         break
    ...     uuids.append(uuid)
    ...
    >>> len(uuids)
    1000

    A machine specific secret is generated on the first invokation,
    encoding all the IP and MAC addresses. This is expensive so is cached
    and reused for all subsequent invokations.

    >>> import canonical.uuid
    >>> canonical.uuid._machine_secret is None
    False
    >>> canonical.uuid._machine_secret = None
    >>> generate_uuid() == generate_uuid()
    False
    >>> canonical.uuid._machine_secret is None
    False
    >>> secret1 = canonical.uuid._machine_secret
    >>> generate_uuid() == generate_uuid()
    False
    >>> secret2 = canonical.uuid._machine_secret
    >>> secret1 is secret2
    True
    """
    # Generate a secret specific to this machines MAC addresses
    global _machine_secret
    if _machine_secret is None:
        ifconfig = subprocess.Popen(
                ['/sbin/ifconfig', '-a'], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, stdin=subprocess.PIPE
                )
        (blob, nothing) = ifconfig.communicate()
        if ifconfig.returncode != 0:
            raise RuntimeError(
                    "Error running ifconfig -a (%d)" % ifconfig.returncode
                    )
        _machine_secret = base(long(sha.new(blob).hexdigest(), 16), 62)

    return base(long(sha.new('%s.%s.%s.%s' % (
        time.time(), random.random(), thread.get_ident(), _machine_secret
        )).hexdigest(), 16), 62)
