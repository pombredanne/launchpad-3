from zope.interface import Interface

__all__ = [ 'IRequestTzInfo' ]

class IRequestTzInfo(Interface):

    def getTzInfo():
        """Returns a tzinfo object that represents the timezone of the
        user.  If the timezone can't be established, a UTC tzinfo object
        is returned."""
