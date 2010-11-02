#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Use this to calculate priorities based on Wiki priority lists such as
# https://launchpad.canonical.com/VersionThreeDotO/Bugs/Inputs


import sys

class Row:
    def __init__(self, scores, trailing):
        self.scores = scores
        self.trailing = trailing


def append_average(items, adjusted_scores, row):
    if len(adjusted_scores) == 0:
        avg = len(rows_of_scores)
    else:
        avg = sum(adjusted_scores)/len(adjusted_scores)
    items.append((avg, "||%4.1f||%s" % (avg, row.trailing)))


def blanks_dont_count(rows_of_scores):
    items = []
    for row in rows_of_scores:
        adjusted_scores = []
        for score in row.scores:
            if score == -1:
                continue
            adjusted_scores.append(score)
        append_average(items, adjusted_scores, row)
    items.sort()
    return items


def blanks_are_heavy(rows_of_scores, half=False):
    items = []
    for row in rows_of_scores:
        adjusted_scores = []
        for score in row.scores:
            if score == -1:
                score = len(rows_of_scores)
                if half:
                    score = score/2
            adjusted_scores.append(score)
        append_average(items, adjusted_scores, row)
    items.sort()
    return items


def less_is_more(rows_of_scores):
    total_per_column = {}
    for row in rows_of_scores:
        scores = row.scores
        for i in range(0, len(scores)):
            score = scores[i]
            total_per_column.setdefault(i, 0)
            if score != -1:
                total_per_column[i] += 1
    print total_per_column
    items = []
    for row in rows_of_scores:
        scores = row.scores
        adjusted_scores = []
        for i in range(0, len(scores)):
            score = scores[i]
            if score == -1:
                score = len(rows_of_scores)
            weight = total_per_column[i]
            adjusted_scores.append(score*weight)
        append_average(items, adjusted_scores, row)
    items.sort()
    return items


def condorcet(rows_of_scores):
    raise NotImplementedError


def parse_scores(str):
    rows = []
    head = []
    tail = []
    ate_first_line = False
    # We drop the first split element because the line starts with a ||
    delta = 1
    for s in str:
        if not s.strip().startswith("||"):
            # Regular output; just output it
            if rows:
                tail.append(s)
            else:
                head.append(s)
            continue

        if not ate_first_line:
            ate_first_line = True
            # Let's take a look at the header
            if s.strip().startswith("|| * "):
                # Get rid of scores since we're recalculating
                delta += 1
                head.append(s)
            else:
                head.append("|| *  " + s)
            continue

        scores = []
        columns = s.split("||")[delta:]
        for col_idx, score in enumerate(columns):
            score = score.strip()
            if score:
                first_char = score[0]
                if not first_char.isdigit() and not first_char == "-":
                    # We hit some text, get out of here
                    break
            try:
                score = float(score)
            except ValueError:
                # If no value was input, we assume it is equivalent to being
                # the last option for this voter.
                score = -1
            scores.append(score)
        rows.append(Row(scores, '||'.join(columns)))
    return rows, head, tail


if __name__ == "__main__":
    str = sys.stdin.read().strip().splitlines()
    rows_of_scores, head, tail = parse_scores(str)
    if len(sys.argv) > 1 and sys.argv[1] == "less-is-more":
        func = less_is_more
    elif len(sys.argv) > 1 and sys.argv[1] == "condorcet":
        func = condorcet
    elif len(sys.argv) > 1 and sys.argv[1] == "blanks-dont-count":
        func = blanks_dont_count
    else:
        func = blanks_are_heavy
    items = func(rows_of_scores)
    print "\n".join(head)
    print "\n".join([i[1] for i in items])
    print "\n".join(tail)

