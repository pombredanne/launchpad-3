# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Branch XMLRPC API."""

__metaclass__ = type
__all__ = [
    'IPublicCodehostingAPI',
    'PublicCodehostingAPI',
    ]


from xmlrpclib import Fault

from bzrlib import urlutils
from zope.component import getUtility
from zope.interface import (
    implementer,
    Interface,
    )

from lp.code.enums import BranchType
from lp.code.errors import (
    CannotHaveLinkedBranch,
    InvalidNamespace,
    NoLinkedBranch,
    NoSuchBranch,
    )
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.code.interfaces.codehosting import (
    BRANCH_ALIAS_PREFIX,
    compose_public_url,
    SUPPORTED_SCHEMES,
    )
from lp.registry.errors import (
    NoSuchDistroSeries,
    NoSuchSourcePackageName,
    )
from lp.registry.interfaces.person import NoSuchPerson
from lp.registry.interfaces.product import (
    InvalidProductName,
    NoSuchProduct,
    )
from lp.registry.interfaces.productseries import NoSuchProductSeries
from lp.services.config import config
from lp.services.webapp import LaunchpadXMLRPCView
from lp.xmlrpc import faults
from lp.xmlrpc.helpers import return_fault


class IPublicCodehostingAPI(Interface):
    """The public codehosting API."""

    def resolve_lp_path(path):
        """Expand the path segment of an lp: URL into a list of branch URLs.

        This method is added to Bazaar in 0.93.

        :return: A dict containing a single 'urls' key that maps to a list of
            URLs. Clients should use the first URL in the list that they can
            support.  Returns a Fault if the path does not resolve to a
            branch.
        """


@implementer(IPublicCodehostingAPI)
class PublicCodehostingAPI(LaunchpadXMLRPCView):
    """See `IPublicCodehostingAPI`."""

    def _compose_http_url(unique_name, path, suffix):
        return compose_public_url('http', unique_name, suffix)

    def _compose_bzr_ssh_url(unique_name, path, suffix):
        if not path.startswith('~'):
            path = '%s/%s' % (BRANCH_ALIAS_PREFIX, path)
        return compose_public_url('bzr+ssh', path, suffix)

    scheme_funcs = {
        'bzr+ssh': _compose_bzr_ssh_url,
        'http': _compose_http_url,
        }

    def _getUrlsForBranch(self, branch, lp_path, suffix=None,
                          supported_schemes=None):
        """Return a list of URLs for the given branch.

        :param branch: A Branch object.
        :param lp_path: The path that was used to traverse to the branch.
        :param suffix: The section of the path that follows the branch
            specification.
        :return: {'urls': [list_of_branch_urls]}.
        """
        if branch.branch_type == BranchType.REMOTE:
            if branch.url is None:
                raise faults.NoUrlForBranch(branch.unique_name)
            return [branch.url]
        else:
            return self._getUniqueNameResultDict(
                branch.unique_name, suffix, supported_schemes, lp_path)

    def _getUniqueNameResultDict(self, unique_name, suffix=None,
                                 supported_schemes=None, path=None):
        if supported_schemes is None:
            supported_schemes = SUPPORTED_SCHEMES
        if path is None:
            path = unique_name
        return [self.scheme_funcs[scheme](unique_name, path, suffix)
                for scheme in supported_schemes]

    @return_fault
    def _resolve_lp_path(self, path):
        """See `IPublicCodehostingAPI`."""
        # Separate method because Zope's mapply raises errors if we use
        # decorators in XMLRPC methods. mapply checks that the passed
        # arguments match the formal parameters. Decorators normally have
        # *args and **kwargs, which mapply fails on.
        strip_path = path.strip('/')
        if strip_path == '':
            raise faults.InvalidBranchIdentifier(path)
        supported_schemes = list(SUPPORTED_SCHEMES)
        hot_products = [product.strip() for product
                        in config.codehosting.hot_products.split(',')]
        # If we have been given something that looks like a branch name, just
        # look that up.
        if strip_path.startswith('~'):
            urls = self._getBranchPaths(strip_path, supported_schemes)
        else:
            # We only check the hot product code when accessed through the
            # short name, so we can check it here.
            if strip_path in hot_products:
                supported_schemes = ['http']
                urls = []
            else:
                urls = [self.scheme_funcs['bzr+ssh'](None, strip_path, None)]
                supported_schemes.remove('bzr+ssh')
            # Try to look up the branch at that url and add alternative URLs.
            # This may well fail, and if it does, we just return the aliased
            # url.
            try:
                urls.extend(
                    self._getBranchPaths(strip_path, supported_schemes))
            except Fault:
                pass
        return dict(urls=urls)

    def _getBranchPaths(self, strip_path, supported_schemes):
        """Get the specific paths for a branch.

        If the branch is not found, but it looks like a branch name, then we
        return a writable URL for it.  If it doesn't look like a branch name a
        fault is raised.
        """
        branch_set = getUtility(IBranchLookup)
        try:
            branch, suffix = branch_set.getByLPPath(strip_path)
        except NoSuchBranch:
            # If the branch isn't found, but it looks like a valid name, then
            # resolve it anyway, treating the path like a branch's unique
            # name. This lets people push new branches up to Launchpad using
            # lp: URL syntax.
            supported_schemes = ['bzr+ssh']
            return self._getUniqueNameResultDict(
                strip_path, supported_schemes=supported_schemes)
        # XXX: JonathanLange 2009-03-21 bug=347728: All of this is repetitive
        # and thus error prone. Alternatives are directly raising faults from
        # the model code(blech) or some automated way of reraising as faults
        # or using a narrower range of faults (e.g. only one "NoSuch" fault).
        except InvalidProductName as e:
            raise faults.InvalidProductName(urlutils.escape(e.name))
        except NoSuchProductSeries as e:
            raise faults.NoSuchProductSeries(
                urlutils.escape(e.name), e.product)
        except NoSuchPerson as e:
            raise faults.NoSuchPersonWithName(urlutils.escape(e.name))
        except NoSuchProduct as e:
            raise faults.NoSuchProduct(urlutils.escape(e.name))
        except NoSuchDistroSeries as e:
            raise faults.NoSuchDistroSeries(urlutils.escape(e.name))
        except NoSuchSourcePackageName as e:
            raise faults.NoSuchSourcePackageName(urlutils.escape(e.name))
        except NoLinkedBranch as e:
            raise faults.NoLinkedBranch(e.component)
        except CannotHaveLinkedBranch as e:
            raise faults.CannotHaveLinkedBranch(e.component)
        except InvalidNamespace as e:
            raise faults.InvalidBranchUniqueName(urlutils.escape(e.name))
        # Reverse engineer the actual lp_path that is used, so we need to
        # remove any suffix that may be there from the strip_path.
        lp_path = strip_path
        if suffix != '':
            # E.g. 'project/trunk/filename.txt' the suffix is 'filename.txt'
            # we want lp_path to be 'project/trunk'.
            lp_path = lp_path[:-(len(suffix) + 1)]
        return self._getUrlsForBranch(
            branch, lp_path, suffix, supported_schemes)

    def resolve_lp_path(self, path):
        """See `IPublicCodehostingAPI`."""
        return self._resolve_lp_path(path)
