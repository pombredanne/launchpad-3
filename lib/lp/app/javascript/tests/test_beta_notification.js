/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

// Set the "enabled" variable, normally set by base-layout-macros.
// This must be a global variable for the code being tested to work.
var privacy_notification_enabled = true;

YUI().use('lp.testing.runner', 'test', 'console', 'node',
          'lp.app.beta_features', 'node-event-simulate', function(Y) {

    var suite = new Y.Test.Suite("lp.app.beta_notification Tests");

    suite.add(new Y.Test.Case({
        name: 'beta-notification',

        _reset_container: function () {
            Y.lp.app.beta_features._reset_beta_notification();
            var body = Y.one(document.body);

            // Replace the container.
            var container = Y.one('#maincontent');
            container.remove(true);
            container = Y.Node.create('<div></div>')
                .set('id', 'maincontent');
            body.appendChild(container);
            body.removeClass('global-notification-visible');
            return container;
        },

        setUp: function () {
            // Create the global notification html.
            var container = this._reset_container();
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            container.appendChild(login_logout);
            window.LP = {
                cache: {}
            };
        },

        test_beta_banner_one_beta_feature: function() {
            LP.cache.related_features = {
                '': {
                    is_beta: true,
                    title: 'A beta feature',
                    url: 'http://lp.dev/LEP/one'
            }};
            Y.lp.app.beta_features.display_beta_notification();

            var body = Y.one('body');
            // The <body> node has the class global-notification-visible,
            // so that the element has enough padding for the beta banner.
            Y.Assert.isTrue(body.hasClass('global-notification-visible'));

            var banner = Y.one('.beta-banner');
            var sub_nodes = banner.get('children');

            // The message about a beta feature consists of the feature
            // title and a link to a page with more information about
            // the feature.
            feature_info = sub_nodes.filter('.beta-feature').item(0);
            Y.Assert.areEqual(
                ' A beta feature (read more)', feature_info.get('text'));
            info_link = feature_info.get('children').item(0);
            Y.Assert.areEqual('http://lp.dev/LEP/one', info_link.get('href'));
        },

        test_beta_banner_two_beta_features: function() {
            LP.cache.related_features = {
                '1': {
                    is_beta: true,
                    title: 'Beta feature 1',
                    url: 'http://lp.dev/LEP/one'
                },
                '2': {
                    is_beta: true,
                    title: 'Beta feature 2',
                    url: ''
                }};
            Y.lp.app.beta_features.display_beta_notification();

            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('global-notification-visible'));

            var banner = Y.one('.beta-banner');
            var sub_nodes = banner.get('children');

            // Notifications about several features can be displayed.
            feature_info = sub_nodes.filter('.beta-feature').item(0);
            Y.Assert.areEqual(
                ' Beta feature 1 (read more)', feature_info.get('text'));
            info_link = feature_info.get('children').item(0);
            Y.Assert.areEqual('http://lp.dev/LEP/one', info_link.get('href'));

            // If an entry in LP.cache.related_features does not provide a
            // "read more" link, the corrsponding node is not added.
            feature_info = sub_nodes.filter('.beta-feature').item(1);
            Y.Assert.areEqual(
                ' Beta feature 2', feature_info.get('text'));
            Y.Assert.isNull(feature_info.get('children').item(0));
        },

        test_beta_banner_no_beta_features_defined: function() {
            LP.cache.related_features = {
                foo_feature: {
                    is_beta: false,
                    title: 'Non-beta feature',
                    url: 'http://example.org'
                }};
            Y.lp.app.beta_features.display_beta_notification();

            var body = Y.one('body');
            Y.Assert.isFalse(body.hasClass('global-notification-visible'));

            Y.Assert.isNull(Y.one('.beta-banner'));
        },

        test_hide_beta_banner: function() {
            LP.cache.related_features = {
                '': {
                    is_beta: true,
                    title: 'A beta feature',
                    url: 'http://lp.dev/LEP/one'
            }};
            Y.lp.app.beta_features.display_beta_notification();
            var body = Y.one('body');
            var banner = Y.one('.beta-banner');
            Y.Assert.isFalse(banner.hasClass('hidden'));

            close_link = Y.one('.global-notification-close');
            close_link.simulate('click');
            // We must wait until the fade out animation finishes.
            this.wait(
                function() {
                    Y.Assert.isTrue(banner.hasClass('hidden'));
                    Y.Assert.isFalse(
                        body.hasClass('global-notification-visible'));
                },
                400);
        }
    }));

    Y.lp.testing.Runner.run(suite);
});

