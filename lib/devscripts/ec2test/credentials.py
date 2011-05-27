# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for reading Amazon Web Service credentials from '~/.ec2/aws_id'."""

__metaclass__ = type
__all__ = [
    'CredentialsError',
    'EC2Credentials',
    ]

import os

import boto
from bzrlib.errors import BzrCommandError
from devscripts.ec2test.account import EC2Account


class CredentialsError(BzrCommandError):
    """Raised when AWS credentials could not be loaded."""

    _fmt = (
        "Please put your aws access key identifier and secret access "
        "key identifier in %(filename)s. (On two lines).  %(extra)s" )

    def __init__(self, filename, extra=None):
        super(CredentialsError, self).__init__(filename=filename, extra=extra)


class EC2Credentials:
    """Credentials for logging in to EC2."""

    DEFAULT_CREDENTIALS_FILE = '~/.ec2/aws_id'

    def __init__(self, identifier, secret):
        self.identifier = identifier
        self.secret = secret

    @classmethod
    def load_from_file(cls, filename=None):
        """Load the EC2 credentials from 'filename'."""
        if filename is None:
            filename = os.path.expanduser(cls.DEFAULT_CREDENTIALS_FILE)
        try:
            aws_file = open(filename, 'r')
        except (IOError, OSError), e:
            raise CredentialsError(filename, str(e))
        try:
            identifier = aws_file.readline().strip()
            secret = aws_file.readline().strip()
        finally:
            aws_file.close()
        return cls(identifier, secret)

    def connect(self, name):
        """Connect to EC2 with these credentials.

        :param name: ???
        :return: An `EC2Account` connected to EC2 with these credentials.
        """
        conn = boto.connect_ec2(self.identifier, self.secret)
        return EC2Account(name, conn)

    def connect_s3(self):
        """Connect to S3 with these credentials.

        :return: A `boto.s3.connection.S3Connection` with these credentials.
        """
        return boto.connect_s3(self.identifier, self.secret)
