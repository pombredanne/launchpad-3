from canonical.lp.placelessauth.interfaces import IPlacelessLoginSource
from canonical.lp.placelessauth.interfaces import IPasswordEncryptor
from zope.app.rdb.interfaces import IZopeDatabaseAdapter
from sqlos.interfaces import IConnectionName
from zope.interface import implements
from zope.app import zapi

from zope.app.security.interfaces import IPrincipal

class LaunchpadLoginSource(object):
    """
    A login source that uses the launchpad SQL database to look up
    principal information.
    """

    implements(IPlacelessLoginSource)

    def getPrincipal(self, id):
        """
        Return a principal based on the person with the provided id.
        """
        conn = self._getDBConnection()
        cur = conn.cursor()
        statement = ('''select id, displayname, givenname, familyname,
        password from person where id=%s''', (id,))
        cur.execute(*statement)
        data = cur.fetchone()
        if data:
            return self._getPrincipal(*data)
        return None

    def getPrincipals(self, name):
        """
        Return a list of principals based on the persons who have email
        addresses starting with "name".
        """
        conn = self._getDBConnection()
        cur = conn.cursor()
        likename = '%%%s%%' % name
        statement = ("""select distinct p.id, displayname, givenname,
        familyname, password from person as p, emailaddress as e where p.id =
        e.person and e.email like %s""", (likename,))
        cur.execute(*statement)
        data = cur.fetchall()
        L = []
        if data:
            for row in data:
                L.append(self._getPrincipal(*row))
        return L

    def getPrincipalByLogin(self, login):
        """
        Return a principal based on the person with the email address
        signified by "login".
        """
        conn = self._getDBConnection()
        cur = conn.cursor()
        statement = ("""select p.id, displayname, givenname, familyname,
        password from person as p, emailaddress as e where p.id
        = e.person and e.email=%s""", (login,))
        cur.execute(*statement)
        data = cur.fetchone()
        if data:
            return self._getPrincipal(*data)
        return None

    def _getPrincipal(self, id, presentationname, givenname, familyname,
                      password):
        return LaunchpadPrincipal(
            id, presentationname, '%s %s' % (givenname, familyname), password
            )
        
    def _getDBConnection(self):
        name = zapi.getUtility(IConnectionName).name
        adapter = zapi.getUtility(IZopeDatabaseAdapter, name)
        conn = adapter()
        return conn

class LaunchpadPrincipal(object):

    implements(IPrincipal)

    def __init__(self, id, title, description, pwd=None):
        self.id = id
        self.title = title
        self.description = description
        self.__pwd = pwd

    def getLogin(self):
        return self.title

    def validate(self, pw):
        encryptor = zapi.getUtility(IPasswordEncryptor)
        return encryptor.validate(pw, self.__pwd)

