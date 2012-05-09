/* Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI.add('lp.app.banner.privacy.test', function (Y) {

    var tests = Y.namespace('lp.app.banner.privacy.test');
    tests.suite = new Y.Test.Suite('lp.app.banner.privacy Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'privacy_tests',

        setUp: function () {
            var main = Y.one('#maincontent');
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            main.appendChild(login_logout);
        },

        tearDown: function () {
            var body = Y.one(document.body);
            var main = Y.one('#maincontent');
            main.remove(true);
            main = Y.Node.create('<div></div>')
                .set('id', 'maincontent');
            body.appendChild(main);
            var login_logout = Y.Node.create('<div></div>')
                .addClass('login-logout');
            main.appendChild(login_logout);
        },

        test_library_exists: function () {
            Y.Assert.isObject(Y.lp.app.banner.privacy,
                "Could not locate the lp.app.banner.privacy module");
        },

        test_init_without_config: function () {
            var banner = new Y.lp.app.banner.privacy.PrivacyBanner();
            Y.Assert.areEqual(
                "The information on this page is private.",
                banner.get('notification_text'));
            Y.Assert.areEqual(
                '<span class="sprite notification-private"></span>',
                banner.get('banner_icon'));
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'lp.app.banner.privacy']});
