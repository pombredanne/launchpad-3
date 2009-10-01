# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to represent a single session of EC2 use."""

__metaclass__ = type
__all__ = [
    'EC2SessionName',
    ]

from devscripts.ec2test.utils import (
    find_datetime_string, make_datetime_string, make_random_string)


class EC2SessionName(str):
    """A name for an EC2 session.

    This is used when naming key pairs and security groups, so it's
    useful to be unique. However, to aid garbage collection of old key
    pairs and security groups, the name contains a common element and
    a timestamp. The form taken should always be:

      <base-name>/<timestamp>/<random-data>

    None of the parts should contain forward-slashes, and the
    timestamp should acceptable input to `find_datetime_string`.

    `EC2SessionName.make()` will generate a suitable name for you.
    """

    @classmethod
    def make(cls, base):
        assert '/' not in base
        return cls("%s/%s/%s" % (
                base, make_datetime_string(), make_random_string()))

    @property
    def base(self):
        parts = self.split('/')
        assert len(parts) == 3
        return parts[0]

    @property
    def timestamp(self):
        parts = self.split('/')
        assert len(parts) == 3
        return find_datetime_string(parts[1])

    @property
    def rand(self):
        parts = self.split('/')
        assert len(parts) == 3
        return parts[2]
