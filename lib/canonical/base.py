"""Convert numbers to an arbitrary base numbering scheme

This file is based on work from the Python Cookbook and is under the Python
license.

"""
__all__ = ['base']

import string
abc = string.digits + string.letters

def base(number, radix):
    """Inverse function to int(str,radix) and long(str,radix)

    >>> base(35, 36)
    'z'

    We can go higher than base 36, but we do this by using upper
    case letters. This is not a standard representation, but
    useful for using this method as a compression algorithm.

    >>> base(61, 62)
    'Z'

    We get identical results to the hex builtin, without the 0x prefix

    >>> [i for i in range(0, 5000, 9) if hex(i)[2:] != base(i, 16)]
    []

    This method is useful for shrinking sha1 and md5 hashes, but keeping
    them in simple ASCII suitable for URL's etc.

    >>> import sha, md5
    >>> s = sha.new('foo').hexdigest()
    >>> s
    '0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33'
    >>> i = long(s, 16)
    >>> i
    68123873083688143418383284816464454849230703155L
    >>> base(i, 62)
    '1HyPQr2xj1nmnkQXBCJXUdQoy5l'
    >>> base(int(md5.new('foo').hexdigest(), 16), 62)
    '5fX649Stem9fET0lD46zVe'

    """
    if not 2 <= radix <= 67:
        raise ValueError, "radix must be in 2..62"

    result = []
    addon = result.append
    if number < 0:
        number = -number
        addon('-')
    elif number == 0:
        addon('0')

    _divmod, _abc = divmod, abc
    while number:
        number, rdigit = _divmod(number, radix)
        addon(_abc[rdigit])

    result.reverse()
    return ''.join(result)

def _test():
    import doctest, base
    doctest.testmod(base)

if __name__ == '__main__':
    _test()
