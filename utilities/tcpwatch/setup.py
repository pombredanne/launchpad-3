#!/usr/bin/env python

from distutils.core import setup

setup(name="tcpwatch",
      version="1.2.1",
      description="TCP monitoring and logging tool with support for HTTP 1.1",
      author="Shane Hathaway",
      author_email="shane@zope.com",
      url="http://hathawaymix.org/Software/TCPWatch",
      scripts=('tcpwatch.py',),
     )

