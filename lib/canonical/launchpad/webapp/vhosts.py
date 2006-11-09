# Copyright 2006 Canonical Ltd.  All rights reserved.

from canonical.config import config


class VirtualHostConfig:

    @staticmethod
    def _hostnameStrToList(hostnamestr):
        """Return list of hostname string.

        >>> thismethod = LaunchpadBrowserFactory._hostnameStrToList
        >>> thismethod('foo')
        ['foo']
        >>> thismethod('foo,bar, baz')
        ['foo', 'bar', 'baz']
        >>> thismethod('foo,,bar, ,baz ,')
        ['foo', 'bar', 'baz']
        >>> thismethod('')
        []
        >>> thismethod(' ')
        []

        """
        if not hostnamestr.strip():
            return []
        return [
            name.strip() for name in hostnamestr.split(',') if name.strip()]

    def __init__(self, hostname, althostnames, rooturl, use_https):
        self.hostname = hostname
        if althostnames is None:
            self.althostnames = []
        else:
            self.althostnames = self._hostnameStrToList(althostnames)
        self.allhostnames = set(self.althostnames + [self.hostname])

        if rooturl is None:
            if use_https:
                protocol = 'https'
            else:
                protocol = 'http'
            rooturl = '%s://%s/' % (protocol, self.hostname)

        self.rooturl = rooturl


class VirtualHostingConfiguration:

    def __init__(self, configuration):
        self.use_https = configuration.use_https
        attrs = set(configuration.getSectionAttributes())
        attrs.remove('use_https')
        self.configs = {}
        for vhostname in attrs:
            vhost = getattr(configuration, vhostname)
            self.configs[vhostname] = VirtualHostConfig(
                vhost.hostname,
                vhost.rooturl,
                vhost.althostnames,
                self.use_https)


vhosts = VirtualHostingConfiguration(config.launchpad.vhosts)


