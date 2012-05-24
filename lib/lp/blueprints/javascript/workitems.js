/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Setup for managing subscribers list for bugs.
 *
 * @module workitems
 * @submodule expanders
 */

YUI.add('lp.workitems.expanders', function(Y) {

    var namespace = Y.namespace('lp.workitems.expanders');

    /**
     * Record of all expanders and their default state.
     */
    var expanders = [];

    /**
     * Attach an expander to each expandable in the page.
     */

    function setUpWorkItemExpanders(){
        Y.all('[class=expandable]').each(function(e) {
            var expander_icon = e.one('[class=expander]');
            // Our parent's first sibling is the tbody we want to collapse.
            var widget_body = e.ancestor().next();
            var expander = new Y.lp.app.widgets.expander.Expander(
                expander_icon, widget_body);
            expander.setUp(true);

            var index = e.ancestor('[class=workitems-group]').get('id');

            // We record the expanders so we can reference them later
            // First we have an array indexed by each milestone
            if (expanders[index] === undefined){
                expanders[index] = [];
            }

            // For each milestone, store an array containing the expander
            // object and the default state for it
            expanders[index].push(new Array(expander,
                                            widget_body.hasClass('default-expanded')));
        });

        Y.all('.expandall_link').on("click", function(link){
            var index = link.currentTarget.get('id');
            index = index.match(/milestone_\d+/)[0];
            Y.Array.forEach(expanders[index], function(expander, i){
                expander[0].render(true, false);
            });
        });

        Y.all('.collapseall_link').on("click", function(link){
            var index = link.currentTarget.get('id');
            index = index.match(/milestone_\d+/)[0];
            Y.Array.forEach(expanders[index], function(expander, i){
                expander[0].render(false, false);
            });
        });

        Y.all('.defaultall_link').on("click", function(link){
            var index = link.currentTarget.get('id');
            index = index.match(/milestone_\d+/)[0];
            Y.Array.forEach(expanders[index], function(expander, i){
                expander[0].render(expander[1], false);
            });
        });
    }
    namespace.setUpWorkItemExpanders = setUpWorkItemExpanders;

}, "0.1", {"requires": ["lp.app.widgets.expander"]});

