# Copyright 2009 Canonical Ltd. All rights reserved.

__metaclass__ = type
__all__ = [
    'validate_shipit_recipientdisplayname',
    'validate_shipit_phone',
    'validate_shipit_city',
    'validate_shipit_addressline1',
    'validate_shipit_addressline2',
    'validate_shipit_organization',
    'validate_shipit_postcode',
    'validate_shipit_province',
    'shipit_postcode_required',
    ]

import re
import string
from textwrap import dedent

from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError


class ShipItAddressValidator:

    def __init__(self, fieldname, length, msg=""):
        self.fieldname = fieldname
        self.length = length
        self.msg = msg

    def __call__(self, value):
        """Check if value contains only ASCII characters and if len(value) is
        smaller or equal self.length.

        >>> ShipItAddressValidator('somefield', 4)(u'some value')
        Traceback (most recent call last):
        ...
        LaunchpadValidationError: The somefield can't have more than 4 characters.
        >>> ShipItAddressValidator('somefield', 14)(u'some value')
        True
        >>> custom_msg = "some custom message"
        >>> ShipItAddressValidator('somefield', 4, custom_msg)(u'some value')
        Traceback (most recent call last):
        ...
        LaunchpadValidationError: some custom message
        """
        _validate_ascii_printable_text(value)
        if len(value) > self.length:
            if not self.msg:
                self.msg = ("The %s can't have more than %d characters."
                            % (self.fieldname, self.length))
            raise LaunchpadValidationError(_(self.msg))
        return True

validate_shipit_organization = ShipItAddressValidator('organization', 30)

validate_shipit_recipientdisplayname = ShipItAddressValidator(
    "recipient's name", 20)

validate_shipit_city = ShipItAddressValidator('city name', 30)

custom_msg = ("Address (first line) can't have more than 30 characters. "
              "You should use the second line if your address is too long.")
validate_shipit_addressline1 = (
    ShipItAddressValidator('address', 30, custom_msg))

custom_msg = ("Address (second line) can't have more than 30 characters. "
              "You should use the first line if your address is too long.")
validate_shipit_addressline2 = (
    ShipItAddressValidator('address', 30, custom_msg))

validate_shipit_phone = ShipItAddressValidator('phone number', 16)

validate_shipit_province = ShipItAddressValidator('province', 30)

validate_shipit_postcode = ShipItAddressValidator('postcode', 15)


def _validate_ascii_printable_text(text):
    """Check if the given text contains only printable ASCII characters.

    >>> print _validate_ascii_printable_text(u'no non-ascii characters')
    None
    >>> print _validate_ascii_printable_text(
    ...     u'\N{LATIN SMALL LETTER E WITH ACUTE}')
    Traceback (most recent call last):
    ...
    LaunchpadValidationError: ...
    >>> print _validate_ascii_printable_text(u'\x06')
    Traceback (most recent call last):
    ...
    LaunchpadValidationError: Non printable characters are not allowed.
    >>> print _validate_ascii_printable_text('\xc3\xa7')
    Traceback (most recent call last):
    ...
    AssertionError: Expected unicode string, but got <type 'str'>
    """
    assert isinstance(text, unicode), (
        'Expected unicode string, but got %s' % type(text))
    try:
        text.encode('ascii')
    except UnicodeEncodeError, unicode_error:
        first_non_ascii_char = text[unicode_error.start:unicode_error.end]
        e_with_acute = u'\N{LATIN SMALL LETTER E WITH ACUTE}'
        raise LaunchpadValidationError(_(dedent("""
            Sorry, but non-ASCII characters (such as '${char}'),
            aren't accepted by our shipping company. Please change
            these to ASCII equivalents. (For instance, '${example}'
            should be changed to 'e')"""),
            mapping={'char': first_non_ascii_char,
                     'example': e_with_acute}))
    if re.search(r"^[%s]*$" % re.escape(string.printable), text) is None:
        raise LaunchpadValidationError(_(
            'Non printable characters are not allowed.'))


# XXX Guilherme Salgado 2006-04-25:
# Not sure if this is the best place for this, but it'll sit here for
# now, as it's not used anywhere else.
_countries_where_postcode_is_required = """
    AT Austria
    DZ Algeria
    AR Argentina
    AM Armenia
    AU Australia
    AZ Azerbaijan
    BH Bahrain
    BD Bangladesh
    BY Belarus
    BE Belgium
    BA Bosnia and Herzegovina
    BR Brazil
    BN Brunei Darussalam
    BG Bulgaria
    CA Canada
    CN China
    CR Costa Rica
    HR Croatia
    CU Cuba
    CY Cyprus
    CZ Czech Republic
    DK Denmark
    DO Dominican Republic
    EC Ecuador
    EG Egypt
    SV El Salvador
    EE Estonia
    FI Finland
    FR France
    GE Georgia
    DE Germany
    GR Greece
    GT Guatemala
    GW Guinea-Bissa
    HT Haiti
    VA Holy See (Vatican City State)
    HN Honduras
    HU Hungary
    IS Iceland
    IN India
    ID Indonesia
    IR Iran, Islamic Republic of
    IL Israel
    IT Italy
    JP Japan
    JO Jordan
    KZ Kazakhstan
    KE Kenya
    KW Kuwait
    KG Kyrgyzstan
    LA Lao People's Democratic Republic
    LV Latvia
    LI Liechtenstein
    LT Lithuania
    LU Luxembourg
    MK Macedonia, Republic of
    MG Madagascar
    MY Malaysia
    MV Maldives
    MT Malta
    MX Mexico
    MD Moldova, Republic of
    MC Monaco
    MN Mongolia
    MA Morocco
    MZ Mozambique
    NP Nepal
    NL Netherlands
    NI Nicaragua
    NO Norway
    OM Oman
    PK Pakistan
    PH Philippines
    PL Poland
    PT Portugal
    RO Romania
    RU Russian Federation
    SA Saudi Arabia
    CS Serbia and Montenegro
    SG Singapore
    SK Slovakia
    SI Slovenia
    ZA South Africa
    KR Korea, Republic of
    ES Spain
    LK Sri Lanka
    SD Sudan
    SZ Swaziland
    SE Sweden
    CH Switzerland
    TJ Tajikistan
    TH Thailand
    TN Tunisia
    TM Turkmenistan
    UA Ukraine
    GB United Kingdom
    US United States
    UY Uruguay
    UZ Uzbekistan
    VE Venezuela
    VN Viet Nam
    ZM Zambia
    """
country_codes_where_postcode_is_required = set(
    line.strip().split(' ', 1)[0]
    for line in _countries_where_postcode_is_required.strip().splitlines())


def shipit_postcode_required(country):
    """Return True if a postcode is required to ship CDs to country.

    >>> class MockCountry: pass
    >>> brazil = MockCountry
    >>> brazil.iso3166code2 = 'BR'
    >>> shipit_postcode_required(brazil)
    True
    >>> zimbabwe = MockCountry
    >>> zimbabwe.iso3166code2 = 'ZWE'
    >>> shipit_postcode_required(zimbabwe)
    False
    """
    code = country.iso3166code2
    return code in country_codes_where_postcode_is_required
