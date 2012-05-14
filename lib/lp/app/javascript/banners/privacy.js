YUI.add('lp.app.banner.privacy', function(Y) {

var ns = Y.namespace('lp.app.banner.privacy');
var baseBanner = Y.lp.app.banner.Banner;

ns.PrivacyBanner = Y.Base.create('privacyBanner', baseBanner, [], {

    renderUI: function () {
        var body = Y.one('body');
        body.addClass('feature-flag-bugs-private-notification-enabled');
        baseBanner.prototype.renderUI.apply(this, arguments);
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
});
}, "0.1", {"requires": ["base", "node", "anim", "lp.app.banner"]});
