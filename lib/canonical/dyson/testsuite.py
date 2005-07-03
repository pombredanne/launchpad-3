#!/usr/bin/env python
"""Test suite for dyson."""

from hct.scaffold import main


tests = [
    "canonical.dyson.tests.test_filter",
    "canonical.dyson.tests.test_hose",
    "canonical.dyson.tests.test_walker",
    ]


if __name__ == "__main__":
    main(names=tests)
