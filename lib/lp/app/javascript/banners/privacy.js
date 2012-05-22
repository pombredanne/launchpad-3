YUI.add('lp.app.banner.privacy', function(Y) {

var ns = Y.namespace('lp.app.banner.privacy');
var baseBanner = Y.lp.app.banner.Banner;

ns.PrivacyBanner = Y.Base.create('privacyBanner', baseBanner, [], {}, {
    ATTRS: {
        banner_id: { value: "privacy-banner" },
        notification_text: {
            value: "The information on this page is private."
        },
        banner_icon: {
            value: '<span class="sprite notification-private"></span>'
        },
    } 
});

// For the privacy banner to work, it needs to have one instance, and one
// instance only.
var _singleton_privacy_banner = null;

ns.getPrivacyBanner = function (banner_text) {
    
    if (_singleton_privacy_banner === null) {
        _singleton_privacy_banner = new ns.PrivacyBanner();
        _singleton_privacy_banner.render();
    }
    if (Y.Lang.isValue(banner_text)) {
        _singleton_privacy_banner.updateText(banner_text); 
    }
    return _singleton_privacy_banner;
}

}, "0.1", {"requires": ["base", "node", "anim", "lp.app.banner"]});
