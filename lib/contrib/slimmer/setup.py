from distutils.core import setup

# patch distutils if it can't cope with the "classifiers" or "download_url"
# keywords (prior to python 2.3.0).
from distutils.dist import DistributionMetadata
if not hasattr(DistributionMetadata, 'classifiers'):
    DistributionMetadata.classifiers = None
if not hasattr(DistributionMetadata, 'download_url'):
    DistributionMetadata.download_url = None
    
setup(
    name = 'slimmer',
    version = '0.1.19',
    description = 'HTML,XHTML,CSS,JavaScript optimizer',
    long_description = """\
slimmer.py
---------------------

Can slim (X)HTML, CSS and Javascript files to become smaller

Required: Python 2.1 or later
Recommended: Python 2.3 or later
""",
    author='Peter Bengtsson',
    author_email = 'peter@fry-it.com',
    url = 'http://www.fry-it.com',
    download_url = 'http://www.fry-it.com/Open-Source/slimmer',
    license = "Python",
    platforms = ['POSIX', 'Windows'],
    keywords = ['slimmer', 'optimizer', 'optimiser', 'whitespace'],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Python Software Foundation License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Communications",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Other/Nonlisted Topic",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    py_modules = ['slimmer',]
    )
