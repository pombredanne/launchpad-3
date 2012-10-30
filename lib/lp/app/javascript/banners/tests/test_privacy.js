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

            var banner_node = Y.Node.create('<div></div>')
                .addClass('yui3-privacybanner');
            main.appendChild(banner_node);
            Y.one('body').appendChild(main);
        },

        tearDown: function () {
            Y.one('#maincontent').remove(true);
            window._singleton_privacy_banner = null;
            delete window.LP;
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
        },

        test_banner_with_custom_text: function () {
            var banner = Y.lp.app.banner.privacy.getPrivacyBanner();
            var new_text = 'New custom text';

            Y.fire('privacy_banner:show', {
                text: new_text
            });
            Y.Assert.areEqual(
                new_text,
                Y.one('.global-notification').get('text'));
            Y.Assert.isTrue(banner.get('visible'),
                            'Banner should be visible.');
        },

        test_banner_hide_event: function () {
            var banner = Y.lp.app.banner.privacy.getPrivacyBanner();
            var new_text = 'New custom text';

            Y.fire('privacy_banner:show', {
                text: new_text
            });
            Y.fire('privacy_banner:hide');
            Y.Assert.isFalse(banner.get('visible'),
                             'Banner should not be visible.');
        },

        test_info_type_private_event: function () {
            var banner = Y.lp.app.banner.privacy.getPrivacyBanner();
            var body = Y.one('body');
            var msg = 'Some private message';
            Y.fire('information_type:is_private', {
                text: msg,
                value: 'PROPRIETARY'
            });
            Y.Assert.areEqual(
                msg,
                Y.one('.global-notification').get('text'));
            Y.Assert.isTrue(body.hasClass('private'),
                            'Body should be private');
            Y.Assert.isTrue(banner.get('visible'),
                            'Banner should be visible.');
        },

        test_info_type_public_event: function () {
            var banner = Y.lp.app.banner.privacy.getPrivacyBanner();
            var new_text = 'New custom text';

            Y.fire('privacy_banner:show', {
                text: new_text
            });
            Y.fire('information_type:is_public');
            var body = Y.one('body');
            Y.Assert.isTrue(body.hasClass('public'), 'Body should be public');
            Y.Assert.isFalse(banner.get('visible'),
                             'Banner should not be visible.');
        }
    }));

}, '0.1', {'requires': ['test', 'test-console', 'lp.app.banner.privacy']});
