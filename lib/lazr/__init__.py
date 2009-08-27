# This is a namespace package for lazr.* packages.  We should absolutely get rid
# of this once we are using eggs.
import warnings
warnings.filterwarnings(
    'ignore',
    'Module .+ was already imported from .+, but .+ is being added.*',
    UserWarning)

import pkg_resources
pkg_resources.declare_namespace('lazr')
