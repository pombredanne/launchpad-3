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

    _getAnimTimes: function() {
        if (this.get('skip_animation')) {
            var anim_times = {
                fade: 0.0,
                slide_out: 0.0,
            }    
        } else {
            var anim_times = {
                fade: 0.3,
                slide_out: 0.2,
            }    
        }

        return anim_times;
    },

    _showBanner: function () {
        var body = Y.one('body');
        body.addClass('global-notification-visible');
        var global_notification = Y.one('.global-notification');
        global_notification.removeClass('hidden');

        var anim_times = this._getAnimTimes();

        var fade_in = new Y.Anim({
            node: global_notification,
            to: {opacity: 1},
            duration: anim_times.fade 
        });
        var body_space = new Y.Anim({
            node: body,
            to: {'paddingTop': '40px'},
            duration: anim_times.slide_out,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '45px'},
            duration: anim_times.slide_out,
            easing: Y.Easing.easeOut
        });

        fade_in.run();
        body_space.run();
        login_space.run();
    },

    _hideBanner: function () {
        var body = Y.one('body');
        var global_notification = Y.one('.global-notification');
        global_notification.addClass('transparent');

        var anim_times = this._getAnimTimes();

        var fade_out = new Y.Anim({
            node: global_notification,
            to: {opacity: 0},
            duration: anim_times.fade 
        });
        var body_space = new Y.Anim({
            node: body,
            to: {'paddingTop': 0},
            duration: anim_times.slide_out,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '6px'},
            duration: anim_times.slide_out,
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

    _createBanner: function () {
        var banner_data = {
            badge: this.get('banner_icon'),
            text: this.get('notification_text'),
            banner_id: this.get('banner_id')
        };
        return Y.lp.mustache.to_html(
            this.get('banner_template'),
            banner_data);
    },

    _updateBanner: function (banner_node) {
        text_node = banner_node.one('.banner-text');
        text_node.set('innerText', this.get('notification_text'));
    },

    renderUI: function() {
        var existing_banner = Y.one('#' + this.get('banner_id'));
        if (existing_banner) {
            this._updateBanner(existing_banner);
        } else {
            var banner_html = this._createBanner(); 
            this.get('contentBox').append(banner_html);
        }
    },

    bindUI: function() {
        this.after('visibleChange', function() {
            if (this.get('visible')) {
                this._showBanner(); 
            } else {
                this._hideBanner(); 
            }
        }); 
    }
}, {
    ATTRS: {
        banner_id: { value: "base-banner" },
        notification_text: { value: "" },
        banner_icon: { value: "<span></span>" },
        banner_template: {
            valueFn: function() {
                return [
                    '<div id="{{ banner_id }}"', 
                        'class="global-notification transparent hidden">', 
                        '{{{ badge }}}',
                        '<span class="banner-text">{{ text }}</span>',
                    "</div>"].join('')
            } 
        },
        skip_animation: { value: false },
        visible: { value: false },
    }
});

}, '0.1', {'requires': ['base', 'node', 'anim', 'widget', 'lp.mustache']});
