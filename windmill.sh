#!/bin/bash

js_testdir=lib/canonical/launchpad/icing/

# We need to set the PYTHONPATH because windmill will look for tests under
# the canonical.launchpad module, which imports some stuff from Zope.
PYTHONPATH=lib/

windmill \
    $@ \
    jsdir=$js_testdir \
    firefox \
    http://launchpad.dev:8085
