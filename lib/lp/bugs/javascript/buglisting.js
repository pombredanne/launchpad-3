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

lp_client = new Y.lp.client.Launchpad();

namespace.rendertable = function(){
    client_listing = Y.one('#client-listing');
    if (client_listing === null){
        return;
    }
    var txt = Mustache.to_html(LP.mustache_listings, LP.cache.mustache_model);
    client_listing.set('innerHTML', txt);
};

}, "0.1", {"requires": ["node"]});
