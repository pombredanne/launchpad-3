# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

# Re-import code from lazr.restful until it can be refactored into a
# utility module.
__all__ = []
import lazr.restful.testing.tales
__all__.extend(lazr.restful.testing.tales.__all__)
from lazr.restful.testing.tales import *
