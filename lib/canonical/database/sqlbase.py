from sqlos import SQLOS
from sqlobject.sqlbuilder import sqlrepr
from datetime import datetime, date, time

__all__ = ['SQLBase', 'quote', 'quote_like']

class SQLBase(SQLOS):
    """Base class to use instead of SQLObject/SQLOS.
    
    Annoying hack to allow us to use SQLOS features in Zope, and plain
    SQLObject outside of Zope.  ("Zope" in this case means the Zope 3 Component
    Architecture, i.e. the basic suite of services should be accessible via
    zope.component.getService)

    By default, this will act just like SQLOS.  If the initZopeless class 
    method is called, it will use the connection you pass to it, and disable 
    all the tricksy per-thread connection stuff that SQLOS does.
    """
    
    zope = True     # Default to behaving like SQLOS

    def initZopeless(cls, connection):
        # Ok, we've been given a plain old connection to use.  Use it, and
        # forget about SQLOS's zope support.
        cls._connection = connection
        cls.zope = False
    initZopeless = classmethod(initZopeless)
    
    def _set_dirty(self, value):
        # If we're running without zope, our connections won't have an
        # IDataManager attached to them.
        if self.zope:
            SQLOS._set_dirty(self, value)
        else:
            self._dirty = value
    dirty = property(SQLOS._get_dirty, _set_dirty)


def quote(x):
    r"""Quote a variable ready for inclusion into an SQL statement.
    Note that you should use quote_like to create a LIKE comparison.

    Basic SQL quoting works

    >>> quote(1)
    '1'
    >>> quote(1.0)
    '1.0'
    >>> quote("hello")
    "'hello'"

    Timezone handling is not implemented, since all timestamps should
    be UTC anyway.

    >>> from datetime import datetime, date, time
    >>> quote(datetime(2003, 12, 4, 13, 45, 50))
    "'2003-12-04 13:45:50'"
    >>> quote(date(2003, 12, 4))
    "'2003-12-04'"
    >>> quote(time(13, 45, 50))
    "'13:45:50'"

    Note that we have to special case datetime handling, as
    SQLObject's quote function is quite broken ( http://tinyurl.com/4bk8p )

    >>> sqlrepr(datetime(2003, 12, 4, 13, 45, 50), 'postgres')
    "'2003-12-04'"
    >>> sqlrepr(date(2003, 12, 4), 'postgres')
    "'2003-12-04'"
    >>> sqlrepr(time(13, 45, 50), 'postgres')
    "'13:45:-1'"

    """
    if isinstance(x, (datetime, date, time)):
        return "'%s'" % x
    return sqlrepr(x, 'postgres')

def quote_like(x):
    r"""Quote a variable ready for inclusion in a SQL statement's LIKE clause

    To correctly generate a SELECT using a LIKE comparision, we need
    to make use of the SQL string concatination operator '||' and the
    quote_like method to ensure that any characters with special meaning
    to the LIKE operator are correctly escaped.

    >>> "SELECT * FROM mytable WHERE mycol LIKE '%%' || %s || '%%'" \
    ...     % quote_like('%')
    "SELECT * FROM mytable WHERE mycol LIKE '%' || '\\\\%' || '%'"

    Note that we need 2 backslashes to quote, as per the docs on
    the LIKE operator. This is because, unless overridden, the LIKE
    operator uses the same escape character as the SQL parser.

    >>> quote_like('100%')
    "'100\\\\%'"
    >>> quote_like('foobar_alpha1')
    "'foobar\\\\_alpha1'"
    >>> quote_like('hello')
    "'hello'"

    Only strings are supported by this method.

    >>> quote_like(1)
    Traceback (most recent call last):
        [...]
    TypeError: Not a string (<type 'int'>)

    """
    if not isinstance(x, basestring):
        raise TypeError, 'Not a string (%s)' % type(x)
    return quote(x).replace('%', r'\\%').replace('_', r'\\_')

