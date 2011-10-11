/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 */
YUI.add('lp.app.batchnavigator', function(Y) {

var namespace = Y.namespace('lp.app.batchnavigator');

function BatchNavigatorHooks(config, lp_client) {
    if (!Y.Lang.isValue(config.contentBox)) {
        Y.error("No contentBox specified in config.");
    }
    this.contentBox = Y.one(config.contentBox);
    if (this.contentBox === null ) {
        Y.error("Invalid contentBox '" + config.contentBox + "' specified in config.");
    }

    if (lp_client === undefined) {
        lp_client = new Y.lp.client.Launchpad();
    }
    this.lp_client = lp_client;
    this.error_handler = new Y.lp.client.ErrorHandler();
    this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);

    if (config.submit_id !== undefined) {
        this.submit_id = config.submit_id;
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
    var self = this;
    Y.Array.each(['first', 'previous', 'next', 'last'], function(link_type) {
        self.contentBox.all('a.'+link_type).each(function(nav_link) {
            var href = nav_link.get('href');
            var link_url = href;
            if (this.link_url_base !== undefined) {
                var urlparts = href.split('?');
                link_url = self.link_url_base + '?' + urlparts[1];
            } else {
                if (link_url.indexOf('batch_request=') < 0) {
                    link_url += '&batch_request=' + self.query_parameter;
                }
            }
            nav_link.addClass('js-action');
            nav_link.on('click', function(e) {
                e.preventDefault();
                self._link_handler(link_url);
            });
        });
    });
    if (this.submit_id !== undefined) {
        this.submit_widgets = [];
        var nav_links = ['upper', 'lower'];
        for (var x=0; x<nav_links.length; x++) {
            var node = Y.one('#' + this.submit_id + '-' + nav_links[x] +
                    ' .batch-navigation-links');
            if (node !== null) {
                this.submit_widgets.push(node);
            }
        }
    }
};

BatchNavigatorHooks.prototype._link_handler = function(link_url) {
    var self = this;
    var y_config = {
        method: "GET",
        headers: {'Accept': 'application/json;'},
        data: '',
        on: {
            start: function() {
                self.showSpinner();
            },
            success: function(id, result) {
                self.hideSpinner();
                self.contentBox.set('innerHTML', result.responseText);
                self._connect_links();
            },
            failure: self.error_handler.getFailureHandler()
        }
    };
    this.lp_client.io_provider.io(link_url, y_config);
};

BatchNavigatorHooks.prototype.showSpinner = function() {
    Y.each(this.submit_widgets, function(widget_node) {
        widget_node.all('a').each(function(nav_link) {
            nav_link.addClass('inactive');
        });
        var spinner_node = Y.Node.create(
        '<img class="spinner" src="/@@/spinner" alt="Loading..." />');
        var first_link = widget_node.one('.first');
        first_link.insertBefore(spinner_node, first_link);
    });
};

BatchNavigatorHooks.prototype.hideSpinner = function() {
    this.contentBox.all('.spinner').remove();
};

}, "0.1", {"requires": ["dom", "node", "event", "io-base", "lp.client"]});
