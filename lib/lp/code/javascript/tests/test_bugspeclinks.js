/* Copyright (c) 2012-2012 Canonical Ltd. All rights reserved. */

YUI.add('lp.code.branch.bugspeclinks.test', function (Y) {
    var module = Y.lp.code.branch.bugspeclinks;
    var extract_candidate_bug_id = module._extract_candidate_bug_id;

    var tests = Y.namespace('lp.code.branch.bugspeclinks.test');
    tests.suite = new Y.Test.Suite('code.branch.bugspeclinks Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'Test bug ID guessing',

        test_no_bug_id_present: function() {
            // If nothing that looks like a bug ID is present, null is
            // returned.
            Y.Assert.isNull(extract_candidate_bug_id('no-id-here'));
        },

        test_short_digit_rund_ignored: function() {
            Y.Assert.isNull(extract_candidate_bug_id('foo-1234-bar'));
        },

        test_leading_zeros_disqualify_potential_ids: function() {
            // Since bug IDs can't start with zeros, any string of numbers
            // with a leading zero are not considered as a potential ID.
            Y.Assert.isNull(extract_candidate_bug_id('foo-0123456-bar'));
            Y.Assert.areEqual(
                extract_candidate_bug_id('foo-0123456-999999-bar'), '999999');
        },

        test_five_digit_bug_ids_are_extracted: function() {
            Y.Assert.areEqual(
                extract_candidate_bug_id('foo-12345-bar'), '12345');
        },

        test_six_digit_bug_ids_are_extracted: function() {
            Y.Assert.areEqual(
                extract_candidate_bug_id('foo-123456-bar'), '123456');
        },

        test_seven_digit_bug_ids_are_extracted: function() {
            Y.Assert.areEqual(
                extract_candidate_bug_id('foo-1234567-bar'), '1234567');
        },

        test_eight_digit_bug_ids_are_extracted: function() {
            Y.Assert.areEqual(
                extract_candidate_bug_id('foo-12345678-bar'), '12345678');
        },

        test_longest_potential_id_is_extracted: function() {
            // Since there may be numbers other than a bug ID in a branch
            // name, we want to extract the longest string of digits.
            Y.Assert.areEqual(
                extract_candidate_bug_id('bug-123456-take-2'), '123456');
            Y.Assert.areEqual(
                extract_candidate_bug_id('123456-1234567'), '1234567');
        }

    }));


}, '0.1', {
    requires: ['test', 'lp.testing.helpers', 'console',
        'lp.code.branch.bugspeclinks', 'node-event-simulate']
});
