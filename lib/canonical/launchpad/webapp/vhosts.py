# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Virtual host handling for the Launchpad webapp."""

from canonical.config import config

__all__ = ['allvhosts']


class VirtualHostConfig:
    """The configuration of a single virtual host."""

    def __init__(self, hostname, althostnames, rooturl, use_https):
        if althostnames is None:
            althostnames = []
        else:
            althostnames = self._hostnameStrToList(althostnames)

        if rooturl is None:
            if use_https:
                protocol = 'https'
            else:
                protocol = 'http'
            rooturl = '%s://%s/' % (protocol, hostname)

        self.hostname = hostname
        self.rooturl = rooturl
        self.althostnames = althostnames

    @staticmethod
    def _hostnameStrToList(althostnames):
        """Return list of hostname strings given a string of althostnames.

        This is to parse althostnames from the launchpad.conf file.

        Basically, it's a comma separated list, but we're quite flexible
        about what is accepted.  See the examples in the following doctest.

        >>> thismethod = VirtualHostConfig._hostnameStrToList
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
        if not althostnames.strip():
            return []
        return [
            name.strip() for name in althostnames.split(',') if name.strip()]


class AllVirtualHostsConfiguration:
    """A representation of the virtual hosting configuration for
    the current Launchpad instance.

    self.use_https : do we use http or https
                    (unless overriden for a particular virutal host)
    self.configs : dict of 'config item name from conf file':VirtualHostConfig.
                   so, like this:
                   {'mainsite': config_for_mainsite,
                    'blueprints': config_for_blueprints,
                     ...
                    }
    self.hostnames : set of hostnames handled by the vhost config
    """

    def __init__(self, launchpad_conf_vhosts):
        """Initialize all virtual host settings from launchpad.conf.

        launchpad_conf_vhosts: The virtual_hosts config item from
        launchpad.conf.

        """
        self.use_https = launchpad_conf_vhosts.use_https

        # Assume all the attributes of the vhosts configuration, except
        # for use_https, will be virtual hosts.
        attrs = set(launchpad_conf_vhosts.getSectionAttributes())
        attrs.remove('use_https')
        set_of_vhosts = attrs

        self.configs = {}
        self.hostnames = set()
        for conf_item_name in set_of_vhosts:
            vhost = getattr(launchpad_conf_vhosts, conf_item_name)
            self.configs[conf_item_name] = config = VirtualHostConfig(
                vhost.hostname,
                vhost.althostnames,
                vhost.rooturl,
                self.use_https)
            self.hostnames.add(config.hostname)
            self.hostnames.update(config.althostnames)


# The only public API to this module, the global virtual host configuration.
allvhosts = AllVirtualHostsConfiguration(config.launchpad.vhosts)

