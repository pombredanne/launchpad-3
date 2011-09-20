/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Code for updating the diff when a new version is available.
 *
 * @module lp.code.branchmergeproposal.updater
 * @requires node, lp.client
 */

YUI.add('lp.code.branchmergeproposal.updater', function(Y) {

// Grab the namespace in order to be able to expose the connect method.
var namespace = Y.namespace('lp.code.branchmergeproposal.updater');

namespace.lp_client = new Y.lp.client.Launchpad();

function UpdaterWidget(config) {
    UpdaterWidget.superclass.constructor.apply(this, arguments);
}

Y.mix(UpdaterWidget, {

    NAME: 'updaterWidget',

    ATTRS: {

        /**
         * Whether or not this MP is still 'pending'.
         *
         * @attribute pending
         * @readOnly
         */
        pending: {
            readOnly: true,
            getter: function() {
                return !Y.Lang.isValue(
                    this.get('srcNode').one('.diff-content'));
            }
        },

        /**
         * Manages whether or not this MP is 'updating' (i.e. the content is
         * about to be updated).
         *
         * @attribute updating
         */
        updating: {
            setter: function(value) {
               if (value) {
                   this._setup_diff_container();
                   this.get(
                       'srcNode').one(
                           'h2').append(
                           '<img src="/@@/spinner" />');
               }
               else {
                   var title = this.get('srcNode').one('h2');
                   if (Y.Lang.isValue(title)) {
                       title.all('img').remove();
                   }
               }
            }
        },

        /**
         * The HTML code for the diff.
         *
         * @attribute diff
         */
        diff: {
            getter: function() {
                if (this.get('pending')) {
                    return '';
                }
                else {
                    return this.get(
                        'srcNode').one('.diff-content').get('innerHTML');
                }
            },
            setter: function(value) {
               this._setup_diff_container();
               this.get(
                   'srcNode').one('.diff-content').set('innerHTML', value);
            }
        }
    }

});

Y.extend(UpdaterWidget, Y.Widget, {

    /*
     * Populate.get('srcNode') with the required nodes to display the diff
     * if needed.
     *
     * @method _setup_diff_container
     */
    _setup_diff_container: function() {
        if (this.get('pending')) {
            // Cleanup.get('srcNode').
            this.get('srcNode').empty();
            // Create the diff container.
            var review_diff = Y.Node.create('<div />')
                .set('id', 'review-diff')
                .append(Y.Node.create('<h2 />')
                    .set("text", "Preview Diff"))
                .append(Y.Node.create('<div />')
                    .addClass("diff-content"));
            this.get('srcNode').append(review_diff);
        }
    },

    /*
     * Update the diff content with the last version.
     *
     * @method update
     */
    update: function() {
        var self = this;
        var config = {
            on: {
                success: function(diff) {
                    self.set('diff', diff);
                    var node = self.get('srcNode').one('.diff-content');
                    Y.lp.anim.green_flash({node: node}).run();
                    self.fire(self.NAME + '.updated');
                },
                failure: function() {
                    var node = self.get('srcNode').one('.diff-content');
                    Y.lp.anim.red_flash({node: node}).run();
                },
                start: function() {
                    self.set('updating', true);
                },
                end: function() {
                    self.set('updating', false);
                }
            }
        };
        var mp_uri = LP.cache.context.web_link;
        namespace.lp_client.get(mp_uri + "/++diff", config);
    }

});



/*
 * Export UpdaterWidget.
 */
namespace.UpdaterWidget = UpdaterWidget;

}, '0.1', {requires: ['node', 'lp.client', 'lp.anim']});
