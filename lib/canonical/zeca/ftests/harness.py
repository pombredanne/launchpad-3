# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
import shutil

import canonical
from canonical.config import config
from canonical.launchpad.daemons.tachandler import TacTestSetup


keysdir = os.path.join(os.path.dirname(__file__), 'keys')


class ZecaTestSetup(TacTestSetup):
    r"""Setup a zeca for use by functional tests

    >>> fixture = ZecaTestSetup()
    >>> fixture.setUp()

    Make sure the server is running

    >>> root_url = 'http://%s:%d' % (
    ...     config.gpghandler.host, config.gpghandler.port)

    We have a hamless application root page

    >>> from urllib import urlopen

    >>> print urlopen(root_url).read()
    Copyright 2004-2009 Canonical Ltd.
    <BLANKLINE>

    A key index lookup form via GET.

    >>> print urlopen(
    ...    '%s/pks/lookup?op=index&search=0xDFD20543' % root_url
    ...    ).read()
    <html>
    ...
    <title>Results for Key 0xDFD20543</title>
    ...
    pub  1024D/DFD20543 2005-04-13 Sample Person (revoked) &lt;sample.revoked@canonical.com&gt;
    ...

    A key content lookup form via GET.

    >>> print urlopen(
    ...    '%s/pks/lookup?op=get&'
    ...    'search=0xA419AE861E88BC9E04B9C26FBA2B9389DFD20543' % root_url
    ...    ).read()
    <html>
    ...
    <title>Results for Key 0xA419AE861E88BC9E04B9C26FBA2B9389DFD20543</title>
    ...
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    Version: GnuPG v1.4.9 (GNU/Linux)
    <BLANKLINE>
    mQGiBEJdmOcRBADkNJPTBuCIefBdRAhvWyD9SSVHh8GHQWS7l9sRLEsirQkKz1yB
    ...

    We can also request a key ID instead of a fingerprint, and it will glob
    for the fingerprint.

    >>> print urlopen(
    ...    '%s/pks/lookup?op=get&'
    ...    'search=0xDFD20543' % root_url
    ...    ).read()
    <html>
    ...
    <title>Results for Key 0xDFD20543</title>
    ...
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    Version: GnuPG v1.4.9 (GNU/Linux)
    <BLANKLINE>
    mQGiBEJdmOcRBADkNJPTBuCIefBdRAhvWyD9SSVHh8GHQWS7l9sRLEsirQkKz1yB
    ...

    If we request a nonexistent key, we get a nice error.

    >>> print urlopen(
    ...    '%s/pks/lookup?op=get&'
    ...    'search=0xDFD20544' % root_url
    ...    ).read()
    <html>
    ...
    <title>Results for Key 0xDFD20544</title>
    ...
    Key Not Found
    ...

    A key submit form via POST (see doc/gpghandler.txt for more information).

    >>> print urlopen('%s/pks/add' % root_url).read()
    <html>
    ...
    <title>Submit a key</title>
    ...

    >>> fixture.tearDown()

    And again for luck

    >>> fixture.setUp()

    >>> print urlopen(root_url).readline()
    Copyright 2004-2009 Canonical Ltd.
    <BLANKLINE>

    >>> fixture.tearDown()
    """
    def setUpRoot(self):
        """Recreate root directory and copy needed keys"""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        shutil.copytree(keysdir, self.root)

    @property
    def root(self):
        return config.zeca.root

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/zeca.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'zeca.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'zeca.log')

