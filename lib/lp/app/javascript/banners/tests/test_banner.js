/* Copyright (c) 2012, Canonical Ltd. All rights reserved. */

YUI.add('lp.app.banner.test', function (Y) {

    var tests = Y.namespace('lp.app.banner.test');
    tests.suite = new Y.Test.Suite('lp.app.banner Tests');

    tests.suite.add(new Y.Test.Case({
        name: 'banner_tests',

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
            Y.Assert.isObject(Y.lp.app.banner,
                "Could not locate the lp.app.banner module");
        },

        test_init_without_config: function () {
            var banner = new Y.lp.app.banner.Banner();
            Y.Assert.areEqual("", banner.get('notification_text'));
            Y.Assert.areEqual("<span></span>", banner.get('banner_icon'));
        },

        test_init_with_config: function () {
            var cfg = {
                notification_text: "Some text.",
                banner_icon: '<span class="sprite"></span>'
            };
            var banner = new Y.lp.app.banner.Banner(cfg);
            Y.Assert.areEqual(
                cfg.notification_text,
                banner.get('notification_text'));
            Y.Assert.areEqual(cfg.banner_icon, banner.get('banner_icon'));
        },

        test_render_no_config: function () {
            var banner = new Y.lp.app.banner.Banner({ skip_animation: true });
            banner.render();

            var banner_node = Y.one(".global-notification");
            Y.Assert.isObject(banner_node);
            Y.Assert.isTrue(banner_node.hasClass('hidden'));
        },

        test_render_with_config: function () {
            var cfg = {
                notification_text: "Some text.",
                banner_icon: '<span class="sprite"></span>',
                skip_animation: true
            };
            var banner = new Y.lp.app.banner.Banner(cfg);
            banner.render();

            var banner_node = Y.one(".global-notification");
            var badge = banner_node.one('.sprite');
            Y.Assert.isObject(banner_node);
            Y.Assert.areEqual(cfg.notification_text, banner_node.get('text'));
            Y.Assert.isObject(badge);
        },

        test_show: function() {
            var banner = new Y.lp.app.banner.Banner({ skip_animation: true });
            banner.render();
            banner.show();
            var banner_node = Y.one(".global-notification");
            Y.Assert.isFalse(banner_node.hasClass('hidden'));
        },

        test_hide: function() {
            var banner = new Y.lp.app.banner.Banner({ skip_animation: true });
            banner.render();
            banner.show();

            // Even with animation times set to 0, this test needs a slight
            // delay in order for the animation end events to fire.
            var banner_node = Y.one(".global-notification");
            var wait_for_anim = 20;
            var check = function () {
                Y.Assert.isTrue(banner_node.hasClass('hidden'));
            };
            banner.hide();
            this.wait(check, wait_for_anim);
        },

        test_updateText: function() {
            var banner = new Y.lp.app.banner.Banner({ skip_animation: true });
            banner.render();
            var new_text = 'some new text';
            banner.updateText(new_text);
            var banner_node = Y.one(".global-notification");
            Y.Assert.areEqual(new_text, banner_node.get('text'));

            banner.updateText();
            banner_node = Y.one(".global-notification");
            Y.Assert.areEqual("", banner_node.get('text'));
        }
    }));

}, '0.1', {'requires': ['test', 'console', 'lp.app.banner']});
