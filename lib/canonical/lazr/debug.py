# Copyright 2008 Canonical Ltd.  All rights reserved.

# Re-import code from lazr.restful until it can be refactored into a
# utility module.
__all__ = []
import lazr.restful.debug
__all__.extend(lazr.restful.debug.__all__)
from lazr.restful.debug import *
