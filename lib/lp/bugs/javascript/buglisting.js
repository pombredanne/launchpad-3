/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Client-side rendering of bug listings.
 *
 * @module bugs
 * @submodule buglisting
 */

YUI.add('lp.bugs.buglisting', function(Y) {

var namespace = Y.namespace('lp.bugs.buglisting');

namespace.rendertable = function(model){
    client_listing = Y.one('#client-listing');
    if (client_listing === null){
        return;
    }
    if (!Y.Lang.isValue(model)){
        model = LP.cache.mustache_model;
    }
    var txt = Mustache.to_html(LP.mustache_listings, model);
    client_listing.set('innerHTML', txt);
};

namespace.update_from_model = function(model){
    namespace.rendertable(model.mustache_model);
};


namespace.update_listing = function(order_by, config){
    load_model_config = {
        io_provider: config.io_provider,
        on: {
            success: namespace.update_from_model
        }
    };
    Y.lp.client.load_model(
        LP.cache.context, '+bugs', load_model_config, 'orderby=' + order_by);
};

}, "0.1", {"requires": ["node", 'lp.client']});
