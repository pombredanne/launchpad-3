/**
 * Add a BetaBanner widget for use.
 *
 * @namespace lp.app.banner
 * @module beta
 *
 */
YUI.add('lp.app.banner.beta', function(Y) {

var ns = Y.namespace('lp.app.banner.beta');
var Banner = Y.lp.app.banner.Banner;

// For the beta banner to work, it needs to have one instance, and one
// instance only.
window._singleton_beta_banner = null;

ns.show_beta_if_needed = function () {
    if (window._singleton_beta_banner === null) {
        var src = Y.one('.yui3-betabanner');
        window._singleton_beta_banner = new ns.BetaBanner({ srcNode: src });
    }
    if (window._singleton_beta_banner.get('features').length !== 0) {
        window._singleton_beta_banner.render();
        window._singleton_beta_banner.show();
    }
};


/**
 * Banner to display for beta features.
 *
 * @class BetaBanner
 * @extends Banner
 *
 */
ns.BetaBanner = Y.Base.create('betaBanner', Banner, [], {

    bindUI: function () {
        Banner.prototype.bindUI.apply(this, arguments);
        var close_box = Y.one('.global-notification-close');
        var that = this;
        close_box.on('click', function(e) {
            e.halt();
            that.hide();
        });
    },

    renderUI: function () {
        var banner_data = {
            badge: this.get('banner_icon'),
            text: this.get('notification_text'),
            features: this.get('features'),
        };
        var banner_html = Y.lp.mustache.to_html(
            this.get('banner_template'),
            banner_data);
        this.get('contentBox').append(banner_html);
        var beta_node = Y.one('.global-notification');
        var close_box = Y.Node.create(
            '<a href="#" class="global-notification-close">Hide' +
            '<span class="notification-close sprite" /></a>');
        beta_node.appendChild(close_box);
    }

}, {
    ATTRS: {
        banner_icon: { value: '<span class="beta-warning">BETA!</span>' },

        banner_template: {
            valueFn: function() {
                return [
                    '<div class="global-notification transparent hidden">',
                        '{{{ badge }}}',
                        '<span class="banner-text">',
                            '{{ text }}{{{ features }}}',
                        '</span>',
                    "</div>"].join('');
            }
        },

        features: {
            valueFn: function () {
                var features_template = [
                    '{{#features}}{{#is_beta}}',
                    '<span class="beta-feature"> {{title}}',
                    '{{#url}}',
                    ' (<a href="{{url}}" class="info-link">read more</a>)',
                    '{{/url}}',
                    '</span>',
                    '{{/is_beta}}{{/features}}'].join('');
                var feature_data = {
                    features: Y.Object.values(LP.cache.related_features)
                };
                return Y.lp.mustache.to_html(features_template, feature_data);
            }
        },

        notification_text: { value: "Some parts of this page are in beta: " }
    }
});


}, '0.1', {'requires': ['base', 'node', 'anim', 'lp.mustache',
                        'lp.app.banner']});
