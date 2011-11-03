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
 * navigation_indices is a YUI NodeList of nodes to update with the current
 * batch info.
 * io_provider is something providing the Y.io interface, typically used for
 * testing.  Defaults to Y.io.
 */
namespace.ListingNavigator = function(current_url, cache, template, target,
                                      navigation_indices, io_provider) {
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
    this.backwards_navigation = new Y.NodeList([]);
    this.forwards_navigation = new Y.NodeList([]);
    if (!Y.Lang.isValue(navigation_indices)){
        navigation_indices = new Y.NodeList([]);
    }
    this.navigation_indices = navigation_indices;
    this.batch_info_template = '<strong>{{start}}</strong> &rarr; ' +
        '<strong>{{end}}</strong> of {{total}} results';
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
 * Rewrite all nodes with navigation classes so that they are hyperlinks.
 * Content is retained.
 */
namespace.linkify_navigation = function(){
    Y.each(['previous', 'next', 'first', 'last'], function(class_name){
        Y.all('.' + class_name).each(function(node){
            new_node = Y.Node.create('<a href="#"></a>');
            new_node.addClass(class_name);
            new_node.setContent(node.getContent());
            node.replace(new_node);
        });
    });
};

/**
 * Factory to return a ListingNavigator for the given page.
 */
namespace.ListingNavigator.from_page = function(){
    var target = Y.one('#client-listing');
    var navigation_indices = Y.all('.batch-navigation-index');
    var navigator = new namespace.ListingNavigator(
        window.location, LP.cache, LP.mustache_listings, target,
        navigation_indices);
    namespace.linkify_navigation();
    navigator.backwards_navigation = Y.all('.first,.previous');
    navigator.forwards_navigation = Y.all('.last,.next');
    navigator.clickAction('.first', navigator.first_batch);
    navigator.clickAction('.next', navigator.next_batch);
    navigator.clickAction('.previous', navigator.prev_batch);
    navigator.clickAction('.last', navigator.last_batch);
    navigator.render_navigation();
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
namespace.ListingNavigator.prototype.render = function(){
    var model = this.current_batch.mustache_model;
    var batch_info = Mustache.to_html(this.batch_info_template, {
        start: this.current_batch.start + 1,
        end: this.current_batch.start +
            this.current_batch.mustache_model.bugtasks.length,
        total: this.current_batch.total
    });
    this.target.setContent(Mustache.to_html(this.template, model));
    this.navigation_indices.setContent(batch_info);
    this.render_navigation();
};


/**
 * Enable/disable navigation links as appropriate.
 */
namespace.ListingNavigator.prototype.render_navigation = function(){
    this.backwards_navigation.toggleClass(
        'inactive', this.current_batch.prev === null);
    this.forwards_navigation.toggleClass(
        'inactive', this.current_batch.next === null);
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
    this.render();
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
        this.render();
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
