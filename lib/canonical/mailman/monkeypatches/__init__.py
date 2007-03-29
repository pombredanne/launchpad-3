# Copyright 2007 Canonical Ltd.  All rights reserved.

import os
import re
import errno
import shutil
import subprocess

HERE = os.path.dirname(__file__)


def monkey_patch(mailman_path, config):
    """Monkey-patch an installed Mailman 2.1 tree.

    Rather than maintain a forked tree of Mailman 2.1, we apply a set of
    changes to an installed Mailman tree.  This tree can be found rooted at
    mailman_path.

    This should usually mean just copying a file from this directory into
    mailman_path.  Rather than build a lot of process into the mix, just hard
    code each transformation here.
    """
    # Link to our noop.py module.
    src = os.path.normpath(os.path.join(HERE, 'noop.py'))
    dst = os.path.join(mailman_path, 'Mailman', 'MTA', 'noop.py')
    try:
        os.symlink(src, dst)
    except OSError, e:
        if e.errno <> errno.EEXIST:
            raise
    # Copy over our mm_cfg.py file
    src = os.path.normpath(os.path.join(HERE, 'mm_cfg.py'))
    dst = os.path.join(mailman_path, 'Mailman', 'mm_cfg.py')
    shutil.copyfile(src, dst)
    # Unfortunately, there are a few things that can't be copied verbatim, so
    # set those up from the lp config file now.
    config_file = open(dst, 'a')
    try:
        if config.mailman.build.site_list:
            print >> config_file, 'MAILMAN_SITE_LIST = "%s"\n\n' % \
                  config.mailman.build.site_list
        if config.mailman.smtp:
            mo = re.match(r'(?P<host>\w+)?(?::(?P<port>\d+))',
                          config.mailman.smtp)
            if mo:
                host, port = mo.group('host', 'port')
                if host is None:
                    host = 'localhost'
                if port is None:
                    port = 25
                print >> config_file, 'SMTPHOST = "%s"\nSMTPPORT = "%d"\n' % \
                      (host, port)
    finally:
        config_file.close()
