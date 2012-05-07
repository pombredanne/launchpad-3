/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Notification banner widget
 *
 * @module lp.app.banner
 */

YUI.add('lp.app.banner', function (Y) {

var ns = Y.namespace('lp.app.banner');

ns.Banner = Y.Base.create('banner', Y.Widget, [], {
    initializer: function (cfg) {
        base_cfg = {
            notification_text: "",
            banner_icon: "<span></span>",
            start_hidden: true
        } 
        cfg = Y.merge(base_cfg, cfg);
        this.set('notification_text', cfg.notification_text);
        this.set('banner_icon', cfg.banner_icon);
        this.set('start_hidden', cfg.start_hidden);
    },

    renderUI: function() {
        var banner_data = {
                hidden: this.get('start_hidden'),
                badge: this.get('banner_icon'),
                text: this.get('notification_text')
        };
        var banner_html = Y.lp.mustache.to_html(
            this.get('banner_template'),
            banner_data);
        this.get('target').append(banner_html);
    },

    show: function () {},

    hide: function () {
        var fade_out = new Y.Anim({
            node: '.global-notification',
            to: {opacity: 0},
            duration: 0.3
        });
        var body_space = new Y.Anim({
            node: 'body',
            to: {'paddingTop': 0},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '6px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        fade_out.on('end', function() {
            fade_out.get('node').addClass('hidden');
        });
        body_space.on('end', function() {
            Y.one('body').removeClass('global-notification-visible');
        });

        fade_out.run();
        body_space.run();
        login_space.run();
    }
}, {
    ATTRS: {
        notification_text: { value: "" },
        banner_icon: { value: "<span></span>" },
        target: {
            valueFn: function() {
                return Y.one('#maincontent');
            }
        },
        banner_template: {
            valueFn: function() {
                return [
                    '<div class="global-notification transparent', 
                        '{{#hidden}}',
                            ' hidden',
                        '{{/hidden}}">',
                            '{{{ badge }}}',
                            '{{ text }}',
                    "</div>"].join('')
            } 
        },
        start_hidden: { value: true }
    },
});

}, '0.1', {'requires': ['base', 'node', 'anim', 'lp.mustache']});
