# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Support for issuing discharge macaroons via the OpenID request.

RPs may need to use SSO authority to authorise macaroons issued by other
services.  The simplest way to do this securely as part of a browser
workflow is to piggyback on the OpenID interaction: this makes it
straightforward to request login information if necessary and gives us
CSRF-safe data exchange.

As part of an OpenID authentication request, the RP includes the following
fields:

  openid.ns.macaroon:
    An OpenID 2.0 namespace URI for the extension. It is not strictly
    required for 1.1 requests, but including it is good for forward
    compatibility.

    It must be set to: http://ns.login.ubuntu.com/2016/openid-macaroon

  openid.macaroon.caveat_id
    The SSO third-party caveat ID from the root macaroon that the RP wants
    to discharge.

As part of the positive assertion OpenID response, the following fields
will be provided:

  openid.ns.macaroon:
    (as above)

  openid.macaroon.discharge
    A serialised discharge macaroon for the provided root macaroon.
"""

__metaclass__ = type
__all__ = [
    'MacaroonRequest',
    'MacaroonResponse',
    ]

from openid import oidutil
from openid.extension import Extension
from openid.message import (
    NamespaceAliasRegistrationError,
    registerNamespaceAlias,
    )


MACAROON_NS = 'http://ns.login.ubuntu.com/2016/openid-macaroon'


try:
    registerNamespaceAlias(MACAROON_NS, 'macaroon')
except NamespaceAliasRegistrationError as e:
    oidutil.log(
        'registerNamespaceAlias(%r, %r) failed: %s' % (
            MACAROON_NS, 'macaroon', e))


def get_macaroon_ns(message):
    """Extract the macaroon namespace URI from the given OpenID message.

    @param message: The OpenID message from which to parse the macaroon.
        This may be a request or response message.
    @type message: C{L{openid.message.Message}}

    @returns: the macaroon namespace URI for the supplied message. The
        message may be modified to define a macaroon namespace.
    @rtype: C{str}

    @raise ValueError: when using OpenID 1 if the message defines the
        'macaroon' alias to be something other than a macaroon type.
    """
    # See if there exists an alias for the macaroon type.
    alias = message.namespaces.getAlias(MACAROON_NS)
    if alias is None:
        # There is no alias, so try to add one. (OpenID version 1)
        try:
            message.namespaces.addAlias(MACAROON_NS, 'macaroon')
        except KeyError as why:
            # An alias for the string 'macaroon' already exists, but it's
            # defined for something other than issuing a discharge macaroon.
            raise MacaroonNamespaceError(why[0])

    return MACAROON_NS


class MacaroonNamespaceError(ValueError):
    """The macaroon namespace was not found and could not be created using
    the expected name (there's another extension using the name 'macaroon').

    This is not I{illegal}, for OpenID 2, although it probably indicates a
    problem, since it's not expected that other extensions will re-use the
    alias that is in use for OpenID 1.

    If this is an OpenID 1 request, then there is no recourse. This should
    not happen unless some code has modified the namespaces for the message
    that is being processed.
    """


class MacaroonRequest(Extension):
    """An object to hold the state of a discharge macaroon request.

    @ivar caveat_id: The SSO third-party caveat ID from the root macaroon
        that the RP wants to discharge.
    @type caveat_id: str

    @group Consumer: requestField, getExtensionArgs, addToOpenIDRequest
    @group Server: fromOpenIDRequest, parseExtensionArgs
    """

    ns_alias = 'macaroon'

    def __init__(self, caveat_id=None, macaroon_ns_uri=MACAROON_NS):
        """Initialize an empty discharge macaroon request."""
        Extension.__init__(self)
        self.caveat_id = caveat_id
        self.ns_uri = macaroon_ns_uri

    @classmethod
    def fromOpenIDRequest(cls, request):
        """Create a discharge macaroon request that contains the fields that
        were requested in the OpenID request with the given arguments.

        @param request: The OpenID request
        @type request: openid.server.CheckIDRequest

        @returns: The newly-created discharge macaroon request
        @rtype: C{L{MacaroonRequest}}
        """
        self = cls()

        # Since we're going to mess with namespace URI mapping, don't mutate
        # the object that was passed in.
        message = request.message.copy()

        self.ns_uri = get_macaroon_ns(message)
        args = message.getArgs(self.ns_uri)
        self.parseExtensionArgs(args)

        return self

    def parseExtensionArgs(self, args):
        """Parse the unqualified macaroon request parameters and add them to
        this object.

        This method is essentially the inverse of C{L{getExtensionArgs}}. It
        restores the serialized macaroon request fields.

        If you are extracting arguments from a standard OpenID checkid_*
        request, you probably want to use C{L{fromOpenIDRequest}}, which
        will extract the macaroon namespace and arguments from the OpenID
        request. This method is intended for cases where the OpenID server
        needs more control over how the arguments are parsed than that
        method provides.

           args = message.getArgs(MACAROON_NS)
           request.parseExtensionArgs(args)

        @param args: The unqualified macaroon arguments
        @type args: {str:str}

        @returns: None; updates this object
        """
        self.caveat_id = args.get('caveat_id')

    def getExtensionArgs(self):
        """Get a dictionary of unqualified macaroon request parameters
        representing this request.

        This method is essentially the inverse of C{L{parseExtensionArgs}}.
        It serializes the macaroon request fields.

        @rtype: {str:str}
        """
        args = {}

        if self.caveat_id:
            args['caveat_id'] = self.caveat_id

        return args


class MacaroonResponse(Extension):
    """Represents the data returned in a discharge macaroon response inside
    an OpenID C{id_res} response. This object will be created by the OpenID
    server, added to the C{id_res} response object, and then extracted from
    the C{id_res} message by the Consumer.

    @ivar discharge_macaroon_raw: The serialized discharge macaroon.
    @type discharge_macaroon_raw: str

    @ivar ns_uri: The URI under which the macaroon data was stored in the
        response message.

    @group Server: extractResponse
    @group Consumer: fromSuccessResponse
    @group Read-only dictionary interface: keys, iterkeys, items, iteritems,
        __iter__, get, __getitem__, keys, has_key
    """

    ns_alias = 'macaroon'

    def __init__(self, discharge_macaroon_raw=None,
                 macaroon_ns_uri=MACAROON_NS):
        Extension.__init__(self)
        self.discharge_macaroon_raw = discharge_macaroon_raw
        self.ns_uri = macaroon_ns_uri

    @classmethod
    def extractResponse(cls, request, discharge_macaroon_raw):
        """Take a C{L{MacaroonRequest}} and a serialized discharge macaroon
        and create a C{L{MacaroonResponse}} object containing that data.

        @param request: The macaroon request object.
        @type request: MacaroonRequest

        @param discharge_macaroon_raw: The serialized discharge macaroon.
        @type discharge_macaroon_raw: str

        @returns: a macaroon response object
        @rtype: MacaroonResponse
        """
        return cls(discharge_macaroon_raw, request.ns_uri)

    @classmethod
    def fromSuccessResponse(cls, success_response, signed_only=True):
        """Create a C{L{MacaroonResponse}} object from a successful OpenID
        library response message
        (C{L{openid.consumer.consumer.SuccessResponse}}).

        @param success_response: A SuccessResponse from consumer.complete().
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @param signed_only: Whether to process only data that was signed in
            the C{id_res} message from the server.
        @type signed_only: bool

        @returns: A macaroon response containing the data that was supplied
            with the C{id_res} response.
        @rtype: MacaroonResponse
        """
        self = cls()
        self.ns_uri = get_macaroon_ns(success_response.message)
        if signed_only:
            args = success_response.getSignedNS(self.ns_uri)
        else:
            args = success_response.message.getArgs(self.ns_uri)
        self.discharge_macaroon_raw = args.get('discharge')
        return self

    def getExtensionArgs(self):
        """Get the fields to put in the macaroon namespace when adding them
        to an C{id_res} message.

        @see: openid.extension
        """
        return {'discharge': self.discharge_macaroon_raw}
