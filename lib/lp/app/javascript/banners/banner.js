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

    _showBanner: function () {
        var body = Y.one('body');
        body.addClass('global-notification-visible');

        var global_notification = Y.one('.global-notification');
        global_notification.removeClass('hidden');

        var fade_in = new Y.Anim({
            node: global_notification,
            to: {opacity: 1},
            duration: 0.3
        });
        var body_space = new Y.Anim({
            node: body,
            to: {'paddingTop': '40px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '45px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });

        fade_in.run();
        body_space.run();
        login_space.run();
    },

    _hideBanner: function () {
        var body = Y.one('body');
        var global_notification = Y.one('.global-notification');

        var fade_out = new Y.Anim({
            node: global_notification,
            to: {opacity: 0},
            duration: 0.3
        });
        var body_space = new Y.Anim({
            node: body,
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
            global_notification.addClass('hidden');
        });
        body_space.on('end', function() {
            body.removeClass('global-notification-visible');
        });

        fade_out.run();
        body_space.run();
        login_space.run();
    },

    _createBanner: function() {
        var banner_data = {
            badge: this.get('banner_icon'),
            text: this.get('notification_text'),
            banner_id: this.get('banner_id')
        };
        var banner_html = Y.lp.mustache.to_html(
            this.get('banner_template'),
            banner_data);
        this.get('target').append(banner_html);
    },

    _updateBanner: function(existing_banner) {
        existing_banner.set('text', this.get('notification_text'));
    },

    renderUI: function() {
        var existing_banner = Y.one('#' + this.get('banner_id'));
        if (existing_banner) {
            this._updateBanner(existing_banner); 
        } else {
            this._createBanner(); 
        }
    },

    bindUI: function() {
        this.on('visibleChange', function() {
            visible = this.get('visible'); 
            if (visible) {
                this._showBanner(); 
            } else {
                this._hideBanner(); 
            }
        }); 
    }
}, {
    ATTRS: {
        banner_id: { value: this.NAME + "-banner-id" },
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
                    '<div id="{{ banner_id }}"', 
                        'class="global-notification transparent hidden">', 
                        '{{{ badge }}}',
                        '{{ text }}',
                    "</div>"].join('')
            } 
        },
        visible: { value: false },
    },
});

}, '0.1', {'requires': ['base', 'node', 'anim', 'widget', 'lp.mustache']});
