# Copyright 2007 Canonical Ltd.  All rights reserved.

# Hack sys.path to make sure that the Mailman package, which lives inside
# lib/mailman at the top of the Launchpad tree, is importable.

import os
import sys
import canonical

__all__ = ['mailman_path', 'mailman_bin']

launchpad_top   = os.path.dirname(os.path.dirname(canonical.__file__))
mailman_path    = os.path.join(launchpad_top, 'mailman')
mailman_bin     = os.path.join(mailman_path, 'bin')

sys.path.append(mailman_path)

# XXX BarryWarsaw 04-Apr-2007 importfascist will complain when we do
#
# from Mailman.Defaults import *
#
# but that is a common Mailman idiom.  We don't want to modify the
# Mailman/Defaults.py.in file because we don't want to fork the upstream
# code.  The following works around this by poking a fake __all__ into that
# module.  Alternatively, we could whitelist this in importfascist; in
# consultation with Kiko and Stevea, there seemed to be no preference, but I
# think I like keeping all the Mailman-specific hacks inside the
# canonical.mailman package as much as possible.
import Mailman.Defaults
Mailman.Defaults.__all__ = dir(Mailman.Defaults)
