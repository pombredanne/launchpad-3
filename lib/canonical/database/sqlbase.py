from sqlos import SQLOS
from sqlobject.sqlbuilder import sqlrepr

__all__ = ['SQLBase', 'quote']

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
    """Quote a variable ready for inclusion into an SQL statement"""
    return sqlrepr(x, 'postgres')

