/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI({
    base: '../../../../canonical/launchpad/icing/yui/',
    filter: 'raw', combine: false,
    fetchCSS: false,
    }).use('test', 'console', 'node', 'node-event-simulate',
           'lp.answers.question_spam', function(Y) {

    var suite = new Y.Test.Suite("lp.answers.question_spam Tests");

    suite.add(new Y.Test.Case({
        name: 'question_spam',

        setUp: function() {
            // Monkeypatch LP to avoid network traffic and to allow
            // insertion of test data.
            window.LP = {
                links: {},
                cache: {}
            };
            Y.lp.client.Launchpad = function() {};
            Y.lp.client.Launchpad.prototype.named_post =
                function(url, func, config) {
                    LP.cache.call_data = {
                        called_url: url, 
                        called_func: func,
                        called_config: config
                    }
                    // our setup assumes success, so we just do the
                    // success callback.
                    config.on.success();
                };
            LP.cache.context = {
                self_link: 'https://launchpad.dev/api/devel/questions/fake'
            };
        },

        test_mark_as_spam: function () {
            link = Y.one('#mark-spam-1');
            comment = Y.one('.boardComment');
            Y.lp.answers.question_spam.toggle_spam_setting(link);
            Y.Assert.isTrue(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Mark as not spam', link.get('text'),
                'Link text should be \'Mark as not spam\'');
            Y.Assert.areEqual(
                'https://launchpad.dev/api/devel/questions/fake',
                LP.cache.call_data.called_url, 'Call with wrong url.');
            Y.Assert.areEqual(
                'setCommentVisibility', LP.cache.call_data.called_func,
                'Call with wrong func.');
            Y.Assert.isFalse(
                LP.cache.call_data.called_config.parameters.visible);
            Y.Assert.areEqual(
                0, LP.cache.call_data.called_config.parameters.comment_number,
                'Called with wrong wrong comment number.')
            },
        
        test_mark_as_not_spam: function () {
            link = Y.one('#mark-spam-2');
            comment = Y.one('#hidden-comment');
            Y.lp.answers.question_spam.toggle_spam_setting(link);
            Y.Assert.isFalse(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Mark as spam', link.get('text'),
                'Link text should be \'Mark as spam\'')
            Y.Assert.areEqual(
                'https://launchpad.dev/api/devel/questions/fake',
                LP.cache.call_data.called_url, 'Call with wrong url.');
            Y.Assert.areEqual(
                'setCommentVisibility', LP.cache.call_data.called_func,
                'Call with wrong func.');
            Y.Assert.isTrue(
                LP.cache.call_data.called_config.parameters.visible);
            Y.Assert.areEqual(
                1, LP.cache.call_data.called_config.parameters.comment_number,
                'Called with wrong wrong comment number.')
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

