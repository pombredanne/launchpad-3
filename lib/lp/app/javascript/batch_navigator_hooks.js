/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 */
YUI.add('lp.app.batchnavigator', function(Y) {

var namespace = Y.namespace('lp.app.batchnavigator');

function BatchNavigatorHooks(config, lp_client) {
    if (lp_client === undefined) {
        lp_client = new Y.lp.client.Launchpad();
    }
    this.lp_client = lp_client;
    this.error_handler = new Y.lp.client.ErrorHandler();

    if (!Y.Lang.isValue(config.contentBox)) {
        Y.error("No contentBox specified in config.");
    }
    this.contentBox = Y.one(config.contentBox);
    if (this.contentBox === null ) {
        Y.error("Invalid contentBox '" + config.contentBox + "' specified in config.");
    }
    if (config.view_link !== undefined) {
        var link_url_base = LP.cache.context.self_link + '/' + config.view_link;
        this.link_url_base = link_url_base.replace('/api/devel', '');
    }
    this.query_parameter = 'True';
    if (config.query_parameter !== undefined) {
        this.query_parameter = config.query_parameter;
    }
    this.post_refresh_hook = config.post_refresh_hook;
    this._connect_links();
}

namespace.BatchNavigatorHooks = BatchNavigatorHooks;

BatchNavigatorHooks.prototype._connect_links = function() {
    if (Y.Lang.isFunction(this.post_refresh_hook)) {
        this.post_refresh_hook();
    }    
    var batchnav = this;
    Y.Array.each(['first', 'previous', 'next', 'last'], function(link_type) {
        batchnav.contentBox.all('a.'+link_type).each(function(nav_link) {
            var href = nav_link.get('href');
            var link_url = href;
            if (this.link_url_base !== undefined) {
                var urlparts = href.split('?');
                link_url = batchnav.link_url_base + '?' + urlparts[1];
            } else {
                if (link_url.indexOf('batch_request=') < 0) {
                    link_url += '&batch_request=' + batchnav.query_parameter;
                }
            }
            nav_link.addClass('js-action');
            nav_link.on('click', function(e) {
                e.preventDefault();
                batchnav._link_handler(link_url);
            });
        });
    });
};

BatchNavigatorHooks.prototype._link_handler = function(link_url) {
    var batchnav = this;
    var y_config = {
        method: "GET",
        headers: {'Accept': 'application/json;'},
        data: '',
        on: {
            success: function(id, result) {
                batchnav.contentBox.set('innerHTML', result.responseText);
                batchnav._connect_links();
            },
            failure: batchnav.error_handler.getFailureHandler()
        }
    };
    this.lp_client.io_provider.io(link_url, y_config);
};

}, "0.1", {"requires": ["dom", "node", "event", "io-base", "lp.client"]});
