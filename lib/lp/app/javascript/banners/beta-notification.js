YUI.add('lp.app.banner.beta', function(Y) {

var ns = Y.namespace('lp.app.banner.beta');
var baseBanner = Y.lp.app.banner.Banner;

ns.BetaBanner = Y.Base.create('betaBanner', baseBanner, [], {

    _createBanner: function () {
        var banner_data = {
            badge: this.get('banner_icon'),
            text: this.get('notification_text'),
            features: this.get('features'),
            banner_id: this.get('banner_id')
        };
        return Y.lp.mustache.to_html(
            this.get('banner_template'),
            banner_data);
    },

    renderUI: function () {
        baseBanner.prototype.renderUI.apply(this, arguments);
        var beta_node = Y.one('.global-notification');
        var close_box = Y.Node.create(
            '<a href="#" class="global-notification-close">Hide' +
            '<span class="notification-close sprite" /></a>');
        beta_node.appendChild(close_box);
    },

    bindUI: function () {
        baseBanner.prototype.bindUI.apply(this, arguments);
        var close_box = Y.one('.global-notification-close');
        var that = this;
        close_box.on('click', function(e) {
            e.halt();
            that.hide();
        })
    },

}, {
    ATTRS: {
        banner_id: { value: "beta-banner" },
        notification_text: { value: "Some parts of this page are in beta: " },
        banner_icon: { value: '<span class="beta-warning">BETA!</span>' },
        banner_template: {
            valueFn: function() {
                return [
                    '<div id="{{ banner_id }}"', 
                        'class="global-notification transparent hidden">', 
                        '{{{ badge }}}',
                        '<span class="banner-text">',
                            '{{ text }}{{{ features }}}',
                        '</span>',
                    "</div>"].join('')
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
                }
                return Y.lp.mustache.to_html(features_template, feature_data);
            }
        },
    }
});

ns.show_beta_if_needed = function () {
    var banner = new ns.BetaBanner();
    if (banner.get('features').length !== 0) {
        banner.render();
        banner.show();
    }
}

}, '0.1', {'requires': ['base', 'node', 'anim', 'lp.mustache',
                        'lp.app.banner']});
