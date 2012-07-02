/* Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI.add('lp.app.banner.privacy.test', function (Y) {

    var tests = Y.namespace('lp.app.banner.privacy.test');
    tests.suite = new Y.Test.Suite('lp.app.banner.privacy Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'privacy_tests',

        setUp: function () {
            var main = Y.Node.create('<div id="maincontent"></div>');
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            main.appendChild(login_logout);
            Y.one('body').appendChild(main);
        },

        tearDown: function () {
            Y.one('#maincontent').remove(true);
            Y.all('.yui3-banner').remove(true);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.banner.privacy,
                "Could not locate the lp.app.banner.privacy module");
        },

        test_init: function () {
            var banner = new Y.lp.app.banner.privacy.PrivacyBanner();
            Y.Assert.areEqual(
                "The information on this page is private.",
                banner.get('notification_text'));
            Y.Assert.areEqual(
                '<span class="sprite notification-private"></span>',
                banner.get('banner_icon'));
        },

        test_only_one_banner: function () {
            // getPrivacyBanner only returns one banner.
            var banner = Y.lp.app.banner.privacy.getPrivacyBanner();
            Y.Assert.areEqual(1, Y.all('.global-notification').size());

            var new_text = 'This is new text';
            banner = Y.lp.app.banner.privacy.getPrivacyBanner(new_text);
            Y.Assert.areEqual(1, Y.all('.global-notification').size());
            var banner_node = Y.one('.global-notification');
            Y.Assert.areEqual(
                new_text,
                Y.one('.global-notification').get('text'));
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'lp.app.banner.privacy']});
