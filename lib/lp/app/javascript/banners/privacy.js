/**
 * Add a PrivacyBanner widget for use.
 *
 * @namespace lp.app.banner
 * @module privacy
 *
 */
YUI.add('lp.app.banner.privacy', function(Y) {

var ns = Y.namespace('lp.app.banner.privacy');
var Banner = Y.lp.app.banner.Banner;

// For the privacy banner to work, it needs to have one instance, and one
// instance only.
var window._singleton_privacy_banner = null;
ns.getPrivacyBanner = function (banner_text, skip_animation) {
    if (window._singleton_privacy_banner === null) {
        var src = Y.one('.yui3-privacybanner');
        window._singleton_privacy_banner = new ns.PrivacyBanner(
            { srcNode: src, skip_animation: skip_animation });
        window._singleton_privacy_banner.render();
    }
    if (Y.Lang.isValue(banner_text)) {
        window._singleton_privacy_banner.updateText(banner_text);
    }
    return window._singleton_privacy_banner;
};


/**
 * Banner to display when page contains private information.
 *
 * @class PrivacyBanner
 * @extends Banner
 *
 */
ns.PrivacyBanner = Y.Base.create('privacyBanner', Banner, [], {}, {
    bindUI: function () {
        that = this;
        Banner.prototype.bindUI.apply(this, arguments);
        Y.on('information_type:is_public', that.show, that);
        Y.on('information_type:is_private', that.hide, that);
    },

    ATTRS: {
        banner_icon: {
            value: '<span class="sprite notification-private"></span>'
        },
        notification_text: {
            value: "The information on this page is private."
        }
    }
});

}, "0.1", {
    requires: ["base", "node", "anim", "lp.app.banner",
               "lp.app.information_type"]
});
