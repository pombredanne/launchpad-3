# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helpers for doing natural language phrase search using the
full text index.
"""

__metaclass__ = type

__all__ = ['nl_phrase_search']

import re

from canonical.database.sqlbase import cursor, quote, sqlvalues

# Regular expression to extract terms from the printout of a ts_query
TS_QUERY_TERM_RE = re.compile(r"'([^']+)'")


def nl_term_candidates(phrase):
    """Returns in an array the candidate search terms from phrase.
    Stop words are removed from the phrase and every term is normalized
    according to the full text rules (lowercased and stemmed).

    :phrase: a search phrase
    """
    cur = cursor()
    cur.execute("SELECT ftq(%(phrase)s)" % sqlvalues(phrase=phrase))
    rs = cur.fetchall()
    assert len(rs) == 1, "ftq() returned more than one row"
    terms = rs[0][0]
    if not terms:
        # Only stop words
        return []
    return TS_QUERY_TERM_RE.findall(terms)


def nl_phrase_search(phrase, table, constraints='',
                     extra_constraints_tables=None):
    """Return the tsearch2 query that should be use to do a phrase search.

    This function implement an algorithm similar to the one used by MySQL
    natural language search (as documented at
    http://dev.mysql.com/doc/refman/5.0/en/fulltext-search.html).

    It eliminates stop words from the phrase and normalize each terms
    according to the full text indexation rules (lowercasing and stemming).

    Each term that is present in more than 50% of the candidate rows is also
    eliminated from the query. That term eliminatation is only done when there
    are 5 candidate rows or more.

    The remaining terms are then ORed together. One should use the rank() or
    rank_cd() function to order the results from running that query. This will
    make rows that use more of the terms and for which the terms are found
    closer in the text at the top of the list, while still returning rows that
    use only some of the terms.

    :phrase: A search phrase.

    :table: This should be the SQLBase class representing the base type.

    :constraints: Additional SQL clause that limits the rows to a
    subset of the table.

    :extra_constraints_tables: A list of additional table names that are
    needed by the constraints clause.

    Caveat: The SQLBase class must define a 'fti' column .
    This is the column that is used for full text searching.
    """
    total = table.select(
        constraints, clauseTables=extra_constraints_tables).count()
    term_candidates = nl_term_candidates(phrase)
    if total < 5:
        return '|'.join(term_candidates)

    # Build the query to get all the counts. We get all the counts in
    # one query, using COUNT(CASE ...), since issuing separate queries
    # with COUNT(*) is a lot slower.
    count_template = (
        'COUNT(CASE WHEN %(table)s.fti @@ ftq(%(term)s)'
        ' THEN TRUE ELSE null END)')
    select_counts = [
        count_template % {'table': table._table, 'term': quote(term)}
        for term in term_candidates
        ]
    select_tables = [table._table]
    if extra_constraints_tables is not None:
        select_tables.extend(extra_constraints_tables)
    count_query = "SELECT %s FROM %s" % (
        ', '.join(select_counts), ', '.join(select_tables))
    if constraints != '':
        count_query += " WHERE %s" % constraints
    cur = cursor()
    cur.execute(count_query)
    counts = cur.fetchone()

    # Remove words that are too common.
    terms = [
        term for count, term in zip(counts, term_candidates)
        if float(count) / total < 0.5
        ]
    return '|'.join(terms)
