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
    },

    /**
     * The records in the current batch have been changed by another component.
     * The model attribute 'total' is adjusted according to the value of
     * total_delta and the navigator rendered to reflect the change.
     * If the new sharee size is 0, we attempt to navigate to the next or
     * previous batch so that any remaining records are displayed.
     * @param new_sharees
     * @param total_delta
     */
    update_batch_totals: function(new_sharees, total_delta) {
        var model = this.get('model');
        var batch_key = model.get_batch_key(this.get_current_batch());
        var current_total = model.get('total');
        this.get('batches')[batch_key].sharee_data = new_sharees;
        model.set('total', current_total + total_delta);
        this.render_navigation();
        if (new_sharees.length === 0) {
            if (this.has_prev()) {
                this.prev_batch();
            } else if (this.has_next()) {
                this.next_batch();
            }
        }
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
