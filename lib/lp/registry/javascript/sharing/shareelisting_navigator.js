/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Batch navigation support for sharees.
 *
 * @module registry
 * @submodule sharing
 */

YUI.add('lp.registry.sharing.shareelisting_navigator', function (Y) {

var namespace = Y.namespace(
    'lp.registry.sharing.shareelisting_navigator');

var
    NAME = "shareeListingNavigator",
    // Events
    UPDATE_CONTENT = 'updateContent';

function ShareeListingNavigator(config) {
    ShareeListingNavigator.superclass.constructor.apply(this, arguments);
}

Y.extend(ShareeListingNavigator, Y.lp.app.listing_navigator.ListingNavigator, {

    initializer: function(config) {
        this.publish(UPDATE_CONTENT);
    },

    render_content: function() {
        var current_batch = this.get_current_batch();
        this.fire(UPDATE_CONTENT, current_batch.sharee_data);
    },

    /**
     * Return the number of items in the specified batch.
     * @param batch
     */
    _batch_size: function(batch) {
        return batch.sharee_data.length;
    }
});

ShareeListingNavigator.NAME = NAME;
ShareeListingNavigator.UPDATE_CONTENT = UPDATE_CONTENT;
namespace.ShareeListingNavigator = ShareeListingNavigator;

}, '0.1', {
    'requires': [
        'node', 'event', 'lp.app.listing_navigator'
    ]
});
