
import unittest
from zope.testing.doctestunit import DocTestSuite

def test_count_lines():
    '''
    >>> from canonical.rosetta.browser import count_lines
    >>> count_lines("foo")
    1
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a1234566789a123456789")
    1
    >>> count_lines("a\\nb")
    2
    >>> count_lines("a\\nb\\n")
    2
    >>> count_lines("a\\nb\\nc")
    3
    >>> count_lines("123456789a123456789a123456789a\\n1234566789a123456789a")
    2
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a1\\n1234566789a123456789a123456789a")
    3
    >>> count_lines("123456789a123456789a123456789a123456789a123456789a123456789a\\n1234566789a123456789a123456789a")
    3
    '''

def test_suite():
    suite = DocTestSuite()
    return suite

if __name__ == '__main__':
    r = unittest.TextTestRunner()
    r.run(DocTestSuite())

