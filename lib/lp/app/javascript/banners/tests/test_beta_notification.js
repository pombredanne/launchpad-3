/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

// Set the "enabled" variable, normally set by base-layout-macros.
// This must be a global variable for the code being tested to work.
var privacy_notification_enabled = true;

YUI.add('lp.app.banner.beta.test', function (Y) {

    var tests = Y.namespace('lp.app.banner.beta.test');
    tests.suite = new Y.Test.Suite('lp.app.banner.beta Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'beta-notification',

        setUp: function () {
            var main = Y.Node.create('<div id="maincontent"></div>');
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            main.appendChild(login_logout);
            Y.one('body').append(main);
            window.LP = {
                cache: {}
            };
        },

        tearDown: function () {
            Y.one('#maincontent').remove(true);
            Y.all('.yui3-banner').remove(true);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.banner.beta,
                "Could not locate the lp.app.banner.beta module");
        },

        test_beta_banner_one_beta_feature: function() {
            LP.cache.related_features = {
                '': {
                    is_beta: true,
                    title: 'A beta feature',
                    url: 'http://lp.dev/LEP/one'
            }};
            var betabanner = new Y.lp.app.banner.beta.BetaBanner(
                {skip_animation: true});
            betabanner.render();
            betabanner.show();

            var body = Y.one('body');
            // The <body> node has the class global-notification-visible,
            // so that the element has enough padding for the beta banner.
            Y.Assert.isTrue(body.hasClass('global-notification-visible'));

            feature_info = Y.one('.beta-feature');
            // The message about a beta feature consists of the feature
            // title and a link to a page with more information about
            // the feature.
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
            var betabanner = new Y.lp.app.banner.beta.BetaBanner(
                {skip_animation: true});
            betabanner.render();
            betabanner.show();

            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('global-notification-visible'));

            // Notifications about several features can be displayed.
            feature_info = Y.all('.beta-feature').item(0);
            Y.Assert.areEqual(
                ' Beta feature 1 (read more)', feature_info.get('text'));
            info_link = feature_info.get('children').item(0);
            Y.Assert.areEqual('http://lp.dev/LEP/one', info_link.get('href'));

            // If an entry in LP.cache.related_features does not provide a
            // "read more" link, the corrsponding node is not added.
            feature_info = Y.all('.beta-feature').item(1);
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
            Y.lp.app.banner.beta.show_beta_if_needed();
            Y.Assert.isNull(Y.one('.global-notification'));
        },

        test_hide_beta_banner: function() {
            LP.cache.related_features = {
                '': {
                    is_beta: true,
                    title: 'A beta feature',
                    url: 'http://lp.dev/LEP/one'
            }};
            var betabanner = new Y.lp.app.banner.beta.BetaBanner(
                {skip_animation: true});
            betabanner.render();
            betabanner.show();
            var body = Y.one('body');
            var banner = Y.one('.global-notification');
            Y.Assert.isFalse(banner.hasClass('hidden'));

            // Even with animation times set to 0, this test needs a slight
            // delay in order for the animation end events to fire.
            var check = function() {
                Y.Assert.isTrue(banner.hasClass('hidden'));
                Y.Assert.isFalse(
                    body.hasClass('global-notification-visible'));
            };
            close_link = Y.one('.global-notification-close');
            close_link.simulate('click');
            var wait_time = 20;
            this.wait(check, wait_time);
        }
    }));

}, '0.1', { 'requires': ['test', 'console', 'node', 'lp.app.banner.beta',
                         'node-event-simulate']
});
