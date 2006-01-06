# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Various functions that are useful for handling dates/datetimes."""

__metaclass__ = type

from datetime import date, timedelta


def make_mondays_between(start, end):
    """Iteration of dates that are mondays between start and end dates.

    A friday to a monday.

    >>> for monday in make_mondays_between(
    ...         date(2005, 11, 25), date(2006, 1, 9)):
    ...     print monday.isocalendar()
    (2005, 48, 1)
    (2005, 49, 1)
    (2005, 50, 1)
    (2005, 51, 1)
    (2005, 52, 1)
    (2006, 1, 1)
    (2006, 2, 1)

    Test from Tuesday to Monday.

    >>> for day in range(22, 30):
    ...     mondays = make_mondays_between(
    ...         date(2005, 11, day), date(2005, 12, day))
    ...     print date(2005, 11, day).isocalendar(), mondays.next().isoformat()
    (2005, 47, 2) 2005-11-28
    (2005, 47, 3) 2005-11-28
    (2005, 47, 4) 2005-11-28
    (2005, 47, 5) 2005-11-28
    (2005, 47, 6) 2005-11-28
    (2005, 47, 7) 2005-11-28
    (2005, 48, 1) 2005-11-28
    (2005, 48, 2) 2005-12-05
    """
    assert isinstance(start, date)
    assert isinstance(end, date)
    mondaystart = start + timedelta(days=(8 - start.isoweekday()) % 7)
    currentdate = mondaystart
    while currentdate <= end:
        yield currentdate
        currentdate += timedelta(days=7)

def get_date_for_monday(year, week):
    """Return the date of monday for the given iso week in the given year.

    >>> get_date_for_monday(2005, 48).isoformat()
    '2005-11-28'
    >>> get_date_for_monday(2005, 50).isoformat()
    '2005-12-12'
    >>> get_date_for_monday(2005, 51).isoformat()
    '2005-12-19'
    >>> get_date_for_monday(2005, 52).isoformat()
    '2005-12-26'
    >>> get_date_for_monday(2005, 53).isoformat()
    '2006-01-02'
    >>> get_date_for_monday(2005, 54).isoformat()
    '2006-01-09'
    >>> get_date_for_monday(2006, 1).isoformat()
    '2006-01-02'
    >>> get_date_for_monday(2006, 2).isoformat()
    '2006-01-09'
    """
    first_monday = first_monday_in_year(year)
    fm_y, fm_w, fm_d = first_monday.isocalendar()
    weeks_to_add = week - fm_w
    assert weeks_to_add >= 0
    return first_monday + timedelta(weeks=weeks_to_add)

def first_monday_in_year(year):
    """Return the date of the first monday in the year.

    >>> for year in range(1999, 2009):
    ...     first_monday_in_year(year).isoformat()
    '1999-01-04'
    '2000-01-03'
    '2001-01-01'
    '2002-01-07'
    '2003-01-06'
    '2004-01-05'
    '2005-01-03'
    '2006-01-02'
    '2007-01-01'
    '2008-01-07'
    """
    return date(year, 1, (8 - date(year, 1, 1).isoweekday()) % 7 + 1)

