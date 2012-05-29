YUI.add('lp.app.banner.privacy', function(Y) {

var ns = Y.namespace('lp.app.banner.privacy');
var baseBanner = Y.lp.app.banner.Banner;

ns.PrivacyBanner = Y.Base.create('privacyBanner', baseBanner, [], {}, {
    ATTRS: {
        notification_text: {
            value: "The information on this page is private."
        },
        banner_icon: {
            value: '<span class="sprite notification-private"></span>'
        }
    }
});

// For the privacy banner to work, it needs to have one instance, and one
// instance only.
var _singleton_privacy_banner = null;
ns.getPrivacyBanner = function (banner_text, skip_animation) {
    if (_singleton_privacy_banner === null) {
        var src = Y.one('.yui3-privacybanner');
        _singleton_privacy_banner = new ns.PrivacyBanner(
            { srcNode: src, skip_animation: skip_animation });
        _singleton_privacy_banner.render();
    }
    if (Y.Lang.isValue(banner_text)) {
        _singleton_privacy_banner.updateText(banner_text);
    }
    return _singleton_privacy_banner;
};

}, "0.1", {"requires": ["base", "node", "anim", "lp.app.banner"]});
