# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Code to represent a single session of EC2 use."""

__metaclass__ = type
__all__ = [
    'EC2SessionName',
    ]

from datetime import datetime, timedelta

from devscripts.ec2test.utils import (
    find_datetime_string, make_datetime_string, make_random_string)


DEFAULT_LIFETIME = timedelta(hours=6)


class EC2SessionName(str):
    """A name for an EC2 session.

    This is used when naming key pairs and security groups, so it's
    useful to be unique. However, to aid garbage collection of old key
    pairs and security groups, the name contains a common element and
    an expiry timestamp. The form taken should always be:

      <base-name>/<expires-timestamp>/<random-data>

    None of the parts should contain forward-slashes, and the
    timestamp should be acceptable input to `find_datetime_string`.

    `EC2SessionName.make()` will generate a suitable name given a
    suitable base name.
    """

    @classmethod
    def make(cls, base, expires=None):
        """Create an `EC2SessionName`.

        This checks that `base` does not contain a forward-slash, and
        provides some convenient functionality for `expires`:

        - If `expires` is None, it defaults to now (UTC) plus
          `DEFAULT_LIFETIME`.

        - If `expires` is a `datetime`, it is converted to a timestamp
          in the correct form.

        - If `expires` is a `timedelta`, it is added to now (UTC) then
          converted to a timestamp.

        - Otherwise `expires` is assumed to be a string, so is checked
          for the absense of forward-slashes, and that a correctly
          formed timestamp can be discovered.

        """
        assert '/' not in base
        if expires is None:
            expires = DEFAULT_LIFETIME
        if isinstance(expires, timedelta):
            expires = datetime.utcnow() + expires
        if isinstance(expires, datetime):
            expires = make_datetime_string(expires)
        else:
            assert '/' not in expires
            assert find_datetime_string(expires) is not None
        rand = make_random_string(8)
        return cls("%s/%s/%s" % (base, expires, rand))

    @property
    def base(self):
        parts = self.split('/')
        if len(parts) != 3:
            return None
        return parts[0]

    @property
    def expires(self):
        parts = self.split('/')
        if len(parts) != 3:
            return None
        return find_datetime_string(parts[1])

    @property
    def rand(self):
        parts = self.split('/')
        if len(parts) != 3:
            return None
        return parts[2]
