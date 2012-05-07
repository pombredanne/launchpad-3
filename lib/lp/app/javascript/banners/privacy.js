YUI.add('lp.app.banner.privacy', function(Y) {

var ns = Y.namespace('lp.app.banner.privacy');
var baseBanner = Y.lp.app.banner.Banner;

ns.PrivacyBanner = Y.Base.create('privacy-banner', baseBanner, [], {
    bindUI: function () {
        this.on('banner-shown', function() {
            var body = Y.one('body');
            body.addClass('feature-flag-bugs-private-notification-enabled');
        }); 
    }
}, {
    ATTRS: {
        notification_text: {
            value: "The information on this page is private."
        },
        banner_icon: {
            value: '<span class="sprite notification-private"></span>'
        },
    } 
})
}, "0.1", {"requires": ["base", "node", "anim", "lp.app.banner"]});
