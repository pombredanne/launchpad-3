/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Tests for lp.code.branch.bugspeclinks.
 *
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false
    }).use('test', 'console', 'node-event-simulate',
        'lp.code.branch.bugspeclinks', function(Y) {

    var module = Y.lp.code.branch.bugspeclinks;
    var extract_candidate_bug_id = module._extract_candidate_bug_id;
    var suite = new Y.Test.Suite("lp.code.branch.bugspeclinks Tests");

    suite.add(new Y.Test.Case({
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

    var handle_complete = function(data) {
        window.status = '::::' + JSON.stringify(data);
        };
    Y.Test.Runner.on('complete', handle_complete);
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    // Start the test runner on Y.after to ensure all setup has had a
    // chance to complete.
    Y.after('domready', function() {
        Y.Test.Runner.run();
    });
});
