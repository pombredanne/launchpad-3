#!/usr/bin/env python
#
# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import print_function

from distutils.sysconfig import get_python_lib
import imp
import os.path
from string import Template
import sys
from textwrap import dedent

from setuptools import (
    find_packages,
    setup,
    )
from setuptools.command.develop import develop
from setuptools.command.easy_install import ScriptWriter


class LPScriptWriter(ScriptWriter):
    """A modified ScriptWriter that uses Launchpad's boilerplate.

    Any script written using this class will set up its environment using
    `lp_sitecustomize` before calling its entry point.

    The standard setuptools handling of entry_points uses
    `pkg_resources.load_entry_point` to resolve requirements at run-time.
    This involves walking Launchpad's entire dependency graph, which is
    rather slow, and we always build all of our "optional" features anyway,
    so we might as well just take the simplified approach of importing the
    modules we need directly.  If we ever want to start using the "extras"
    feature of setuptools then we may want to revisit this.
    """

    template = Template(dedent("""
        import sys

        import ${module_name}

        if __name__ == '__main__':
            sys.exit(${module_name}.${attrs}())
        """))

    @classmethod
    def get_args(cls, dist, header=None):
        """See `ScriptWriter`."""
        if header is None:
            header = cls.get_header()
        for name, ep in dist.get_entry_map("console_scripts").items():
            cls._ensure_safe_name(name)
            script_text = cls.template.substitute({
                "attrs": ".".join(ep.attrs),
                "module_name": ep.module_name,
                })
            args = cls._get_script_args("console", name, header, script_text)
            for res in args:
                yield res


class lp_develop(develop):
    """A modified develop command to handle LP script generation."""

    def _get_orig_sitecustomize(self):
        env_top = os.path.join(os.path.dirname(__file__), "env")
        system_paths = [
            path for path in sys.path if not path.startswith(env_top)]
        try:
            fp, orig_sitecustomize_path, _ = (
                imp.find_module("sitecustomize", system_paths))
            if fp:
                fp.close()
        except ImportError:
            return ""
        if orig_sitecustomize_path.endswith(".py"):
            with open(orig_sitecustomize_path) as orig_sitecustomize_file:
                orig_sitecustomize = orig_sitecustomize_file.read()
                return dedent("""
                    # The following is from
                    # %s
                    """ % orig_sitecustomize_path) + orig_sitecustomize
        else:
            return ""

    def install_wrapper_scripts(self, dist):
        if not self.exclude_scripts:
            for args in LPScriptWriter.get_args(dist):
                self.write_script(*args)

            # Write bin/py for compatibility.  This is much like
            # env/bin/python, but if we just symlink to it and try to
            # execute it as bin/py then the virtualenv doesn't get
            # activated.  We use -S to avoid importing sitecustomize both
            # before and after the execve.
            py_header = LPScriptWriter.get_header("#!python -S")
            py_script_text = dedent("""\
                import os
                import sys

                os.execv(sys.executable, [sys.executable] + sys.argv[1:])
                """)
            self.write_script("py", py_header + py_script_text)

            env_top = os.path.join(os.path.dirname(__file__), "env")
            stdlib_dir = get_python_lib(standard_lib=True, prefix=env_top)
            orig_sitecustomize = self._get_orig_sitecustomize()
            sitecustomize_path = os.path.join(stdlib_dir, "sitecustomize.py")
            with open(sitecustomize_path, "w") as sitecustomize_file:
                sitecustomize_file.write(dedent("""\
                    import os
                    import sys

                    if "LP_DISABLE_SITECUSTOMIZE" not in os.environ:
                        if "lp_sitecustomize" not in sys.modules:
                            import lp_sitecustomize
                            lp_sitecustomize.main()
                    """))
                if orig_sitecustomize:
                    sitecustomize_file.write(orig_sitecustomize)

            # Write out the build-time value of LPCONFIG so that it can be
            # used by scripts as the default instance name.
            instance_name_path = os.path.join(env_top, "instance_name")
            with open(instance_name_path, "w") as instance_name_file:
                print(os.environ["LPCONFIG"], file=instance_name_file)


__version__ = '2.2.3'

setup(
    name='lp',
    version=__version__,
    packages=find_packages('lib'),
    package_dir={'': 'lib'},
    include_package_data=True,
    zip_safe=False,
    maintainer='Launchpad Developers',
    description=('A unique collaboration and Bazaar code hosting platform '
                 'for software projects.'),
    license='Affero GPL v3',
    # this list should only contain direct dependencies--things imported or
    # used in zcml.
    install_requires=[
        'ampoule',
        'auditorclient',
        'auditorfixture',
        'backports.lzma',
        'BeautifulSoup',
        'bzr',
        'celery',
        'cssselect',
        'cssutils',
        'dkimpy',
        # Required for dkimpy
        'dnspython',
        'dulwich',
        'FeedParser',
        'feedvalidator',
        'fixtures',
        'html5browser',
        'httmock',
        'ipython',
        'jsautobuild',
        'launchpad-buildd',
        'launchpadlib',
        'lazr.batchnavigator',
        'lazr.config',
        'lazr.delegates',
        'lazr.enum',
        'lazr.jobrunner',
        'lazr.lifecycle',
        'lazr.restful',
        'lazr.smtptest',
        'lazr.sshserver',
        'lazr.testing',
        'lazr.uri',
        'lpjsmin',
        'Markdown',
        'mechanize',
        'meliae',
        # Pin version for now to avoid confusion with system site-packages.
        'mock==1.0.1',
        'oauth',
        'oops',
        'oops_amqp',
        'oops_datedir_repo',
        'oops_timeline',
        'oops_twisted',
        'oops_wsgi',
        'paramiko',
        'pgbouncer',
        'psycopg2',
        'pyasn1',
        'pygpgme',
        'pyinotify',
        'pymacaroons',
        'pystache',
        'python-debian',
        'python-keystoneclient',
        'python-memcached',
        'python-openid',
        'python-subunit',
        'python-swiftclient',
        'pytz',
        'PyYAML',
        'rabbitfixture',
        'requests',
        'requests-toolbelt',
        'setproctitle',
        'setuptools',
        'six',
        'soupmatchers',
        'Sphinx',
        'storm',
        'subvertpy',
        'testscenarios',
        'testtools',
        'timeline',
        'transaction',
        'Twisted',
        'txfixtures',
        'txlongpoll',
        'txlongpollfixture',
        'txpkgupload',
        'virtualenv-tools3',
        'wadllib',
        'z3c.pt',
        'z3c.ptcompat',
        'zc.zservertracelog',
        'zope.app.appsetup',
        'zope.app.http',
        'zope.app.publication',
        'zope.app.publisher',
        'zope.app.server',
        'zope.app.testing',
        'zope.app.wsgi',
        'zope.authentication',
        'zope.component[zcml]',
        'zope.contenttype',
        'zope.datetime',
        'zope.error',
        'zope.event',
        'zope.exceptions',
        'zope.formlib',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.location',
        'zope.login',
        'zope.pagetemplate',
        'zope.principalregistry',
        'zope.proxy',
        'zope.publisher',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'zope.sendmail',
        'zope.server',
        'zope.session',
        'zope.tal',
        'zope.tales',
        'zope.testbrowser',
        'zope.testing',
        'zope.traversing',
        'zope.viewlet',  # only fixing a broken dependency
        'zope.vocabularyregistry',
        # Loggerhead dependencies. These should be removed once
        # bug 383360 is fixed and we include it as a source dist.
        'Paste',
        'PasteDeploy',
        'SimpleTAL',
    ],
    url='https://launchpad.net/',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
    ],
    cmdclass={
        'develop': lp_develop,
    },
    entry_points=dict(
        console_scripts=[  # `console_scripts` is a magic name to setuptools
            'bingtestservice = '
                'lp.services.sitesearch.bingtestservice:main',
            'build-twisted-plugin-cache = '
                'lp.services.twistedsupport.plugincache:main',
            'combine-css = lp.scripts.utilities.js.combinecss:main',
            'googletestservice = '
                'lp.services.sitesearch.googletestservice:main',
            'harness = lp.scripts.harness:python',
            'iharness = lp.scripts.harness:ipython',
            'ipy = IPython.frontend.terminal.ipapp:launch_new_instance',
            'jsbuild = lp.scripts.utilities.js.jsbuild:main',
            'kill-test-services = lp.scripts.utilities.killtestservices:main',
            'killservice = lp.scripts.utilities.killservice:main',
            'retest = lp.testing.utilities.retest:main',
            'run = lp.scripts.runlaunchpad:start_launchpad',
            'run-testapp = lp.scripts.runlaunchpad:start_testapp',
            'sprite-util = lp.scripts.utilities.spriteutil:main',
            'start_librarian = lp.scripts.runlaunchpad:start_librarian',
            'test = lp.scripts.utilities.test:main',
            'tracereport = zc.zservertracelog.tracereport:main',
            'twistd = twisted.scripts.twistd:run',
            'watch_jsbuild = lp.scripts.utilities.js.watchjsbuild:main',
            'with-xvfb = lp.scripts.utilities.withxvfb:main',
        ]
    ),
)
