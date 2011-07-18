/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI().use('lp.testing.runner', 'test', 'console', 'node',
          'lp.comments.hide', 'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.comments.hide Tests");

    suite.add(new Y.Test.Case({
        name: 'hide_comments',

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
                    };
                    // our setup assumes success, so we just do the
                    // success callback.
                    config.on.success();
                };
            LP.cache.comment_context = {
                self_link: 'https://launchpad.dev/api/devel/some/comment/'
            };
        },

        test_hide: function () {
            link = Y.one('#mark-spam-0');
            comment = Y.one('.boardComment');
            Y.lp.comments.hide.toggle_hidden(link);
            Y.Assert.isTrue(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Unhide comment', link.get('text'),
                'Link text should be \'Unhide comment\'');
            Y.Assert.areEqual(
                'https://launchpad.dev/api/devel/some/comment/',
                LP.cache.call_data.called_url, 'Call with wrong url.');
            Y.Assert.areEqual(
                'setCommentVisibility', LP.cache.call_data.called_func,
                'Call with wrong func.');
            Y.Assert.isFalse(
                LP.cache.call_data.called_config.parameters.visible);
            Y.Assert.areEqual(
                0, LP.cache.call_data.called_config.parameters.comment_number,
                'Called with wrong wrong comment number.');
            },

        test_unhide: function () {
            link = Y.one('#mark-spam-1');
            comment = Y.one('#hidden-comment');
            Y.lp.comments.hide.toggle_hidden(link);
            Y.Assert.isFalse(comment.hasClass('adminHiddenComment'));
            Y.Assert.areEqual('Hide comment', link.get('text'),
                'Link text should be \'Hide comment\'');
            Y.Assert.areEqual(
                'https://launchpad.dev/api/devel/some/comment/',
                LP.cache.call_data.called_url, 'Call with wrong url.');
            Y.Assert.areEqual(
                'setCommentVisibility', LP.cache.call_data.called_func,
                'Call with wrong func.');
            Y.Assert.isTrue(
                LP.cache.call_data.called_config.parameters.visible);
            Y.Assert.areEqual(
                1, LP.cache.call_data.called_config.parameters.comment_number,
                'Called with wrong wrong comment number.');
            }
        }));

    Y.lp.testing.Runner.run(suite);

});

