/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: true,
    }).use('test', 'console', 'node', 'node-event-simulate',
           'lp.answers.question_spam', function(Y) {

    var suite = new Y.Test.Suite("lp.answers.question_spam Tests");

    suite.add(new Y.Test.Case({
        name: 'question_spam',

        test_mark_as_spam: function () {
            link = Y.one('#mark-spam-1');
            comment = Y.one('.boardComment');
            Y.lp.answers.question_spam.toggle_spam_setting(link);
            Y.Assert.isTrue(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Mark as not spam', link.get('text'),
                'Link text should be \'Mark as not spam\'')
            },
        
        test_mark_as_not_spam: function () {
            link = Y.one('#mark-spam-2');
            comment = Y.one('#hidden-comment');
            Y.lp.answers.question_spam.toggle_spam_setting(link);
            Y.Assert.isFalse(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Mark as spam', link.get('text'),
                'Link text should be \'Mark as spam\'')
            },

        }));

    // Lock, stock, and two smoking barrels.
    Y.Test.Runner.add(suite);

    var console = new Y.Console({newestOnTop: false});
    console.render('#log');

    Y.on('domready', function() {
        Y.Test.Runner.run();
        });
});

