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


/**
 * Constructor.
 * current_url is used to determine search params.
 * cache is the JSONRequestCache for the batch.
 * template is the template to use for rendering batches.
 * target is a YUI node to update when rendering batches.
 * io_provider is something providing the Y.io interface, typically used for
 * testing.  Defaults to Y.io.
 */
namespace.ListingNavigator = function(current_url, cache, template, target,
                                      io_provider) {
    var lp_client = new Y.lp.client.Launchpad();
    this.search_params = namespace.get_query(current_url);
    delete this.search_params.start;
    delete this.search_params.memo;
    delete this.search_params.direction;
    delete this.search_params.orderby;
    this.io_provider = io_provider;
    this.current_batch = lp_client.wrap_resource(null, cache);
    this.template = template;
    this.target = target;
    this.batches = {};
};


/**
 * Call the callback when a node matching the selector is clicked.
 *
 * The node is also marked up appropriately.
 */
namespace.ListingNavigator.prototype.clickAction = function(selector,
                                                            callback){
    that = this;
    var nodes = Y.all(selector);
    nodes.on('click', function(e){
        e.preventDefault();
        callback.call(that);
    });
    nodes.addClass('js-action');
};


/**
 * Factory to return a ListingNavigator for the given page.
 */
namespace.ListingNavigator.from_page = function(){
    var target = Y.one('#client-listing');
    var navigator = new namespace.ListingNavigator(
        window.location, LP.cache, LP.mustache_listings, target);
    navigator.clickAction('.first', navigator.first_batch);
    navigator.clickAction('.next', navigator.next_batch);
    navigator.clickAction('.previous', navigator.prev_batch);
    navigator.clickAction('.last', navigator.last_batch);
    return navigator;
};


/**
 * Render bug listings via Mustache.
 *
 * If model is supplied, it is used as the data for rendering the listings.
 * Otherwise, LP.cache.mustache_model is used.
 *
 * The template is always LP.mustache_listings.
 */
namespace.ListingNavigator.prototype.rendertable = function(){
    if (! Y.Lang.isValue(this.target)){
        return;
    }
    var model = this.current_batch.mustache_model;
    var txt = Mustache.to_html(this.template, model);
    this.target.set('innerHTML', txt);
};


/**
 * Get the key for the specified batch, for use in the batches mapping.
 */
namespace.ListingNavigator.get_batch_key = function(config){
    return JSON.stringify([config.order_by, config.memo, config.forwards,
                           config.start]);
};

/**
 * A shim to use the data of an LP.cache to render the bug listings and cache
 * their data.
 *
 * order_by is the ordering used by the model.
 */
namespace.ListingNavigator.prototype.update_from_model = function(model){
    var key = namespace.ListingNavigator.get_batch_key(model);
    this.batches[key] = model;
    this.current_batch = model;
    this.rendertable();
};


/**
 * Return the query vars to use for the specified batch.
 * This includes the search params and the batch selector.
 */
namespace.ListingNavigator.prototype.get_batch_query = function(config){
    var query = Y.merge(this.search_params, {orderby: config.order_by});
    if (Y.Lang.isValue(config.memo)){
        query.memo = config.memo;
    }
    if (Y.Lang.isValue(config.start)){
        query.start = config.start;
    }
    if (config.forwards !== undefined && !config.forwards){
        query.direction = 'backwards';
    }
    return query;
};


/**
 * Update the bug listings.
 *
 * order_by is a string specifying the sort order, as it would appear in a
 * URL.
 */
namespace.ListingNavigator.prototype.change_ordering = function(order_by){
    this.first_batch(order_by);
};


/**
 * Update the display to the specified batch.
 *
 * If the batch is cached, it will be used immediately.  Otherwise, it will be
 * retrieved and cached upon retrieval.
 */
namespace.ListingNavigator.prototype.update = function(config){
    var key = namespace.ListingNavigator.get_batch_key(config);
    var cached_batch = this.batches[key];
    if (Y.Lang.isValue(cached_batch)){
        this.current_batch = cached_batch;
        this.rendertable();
    }
    else {
        this.load_model(config);
    }
};


/**
 * Update the navigator to display the last batch.
 */
namespace.ListingNavigator.prototype.last_batch = function(){
    this.update({
        forwards: false,
        memo: "",
        start: this.current_batch.last_start,
        order_by: this.current_batch.order_by
    });
};


/**
 * Update the navigator to display the first batch.
 *
 * The order_by defaults to the current ordering, but may be overridden.
 */
namespace.ListingNavigator.prototype.first_batch = function(order_by){
    if (order_by === undefined){
        order_by = this.current_batch.order_by;
    }
    this.update({
        forwards: true,
        memo: null,
        start: 0,
        order_by: order_by
    });
};


/**
 * Update the navigator to display the next batch.
 */
namespace.ListingNavigator.prototype.next_batch = function(){
    this.update({
        forwards: true,
        memo: this.current_batch.next.memo,
        start:this.current_batch.next.start,
        order_by: this.current_batch.order_by
    });
};

/**
 * Update the navigator to display the previous batch.
 */
namespace.ListingNavigator.prototype.prev_batch = function(){
    this.update({
        forwards: false,
        memo: this.current_batch.prev.memo,
        start:this.current_batch.prev.start,
        order_by: this.current_batch.order_by
    });
};


/**
 * Load the specified batch via ajax.  Display & cache on load.
 */
namespace.ListingNavigator.prototype.load_model = function(config){
    var query = this.get_batch_query(config);
    var load_model_config = {
        on: {
            success: Y.bind(this.update_from_model, this)
        }
    };
    if (Y.Lang.isValue(this.io_provider)){
        load_model_config.io_provider = this.io_provider;
    }
    Y.lp.client.load_model(
        this.current_batch.context, '+bugs', load_model_config, query);
};


/**
 * Return the query of the specified URL in structured form.
 */
namespace.get_query = function(url){
    var querystring = Y.lp.get_url_query(url);
    return Y.QueryString.parse(querystring);
};


}, "0.1", {"requires": ["node", 'lp.client']});
