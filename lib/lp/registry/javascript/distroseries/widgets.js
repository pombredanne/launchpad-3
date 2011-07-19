/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * DistroSeries Widgets.
 *
 * @module lp.registry.distroseries
 * @submodule widgets
 */

YUI.add('lp.registry.distroseries.widgets', function(Y) {

Y.log('loading lp.registry.distroseries.widgets');

var namespace = Y.namespace('lp.registry.distroseries.widgets');

var formwidgets = Y.lp.app.formwidgets;


/**
 * A table to display, order, delete the selected parent series. Each parent
 * can also be made an overlay, and a component and a pocket selected.
 *
 */
var ParentSeriesListWidget;

ParentSeriesListWidget = function() {
    ParentSeriesListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ParentSeriesListWidget, {

    NAME: 'parentSeriesListWidget',

    ATTRS: {

        /**
         * The DistroSeries the choices in this field should
         * reflect. Takes the form of a list of ids,
         * e.g. ["4", "55"].
         *
         * @property parents
         */
        parents: {
            getter: function() {
                var series = [];
                this.fieldNode.all("tbody > tr.parent").each(
                    function(node) {
                        series.push(
                            node.get('id').replace('parent-',''));
                    }
                );
                return series;
            }
        },
        overlays: {
            getter: function() {
                var overlays = [];
                this.fieldNode.all("tbody > tr.parent").each(
                    function(node) {
                        overlays.push(
                            node.one('input.overlay').get('checked'));
                    }
                );
                return overlays;
            }
        },
        overlay_pockets: {
            getter: function() {
                var overlay_pockets = [];
                this.fieldNode.all("tbody > tr.parent").each(
                    function(node) {
                        var select = node.one('td.pocket').one('select');
                        if (select !== null) {
                            overlay_pockets.push(select.get('value'));
                        }
                        else {
                            overlay_pockets.push(null);
                        }
                    }
                );
                return overlay_pockets;
            }
        },
        overlay_components: {
            getter: function() {
                var overlay_components = [];
                this.fieldNode.all("tbody > tr.parent").each(
                    function(node) {
                        var select = node.one('td.component').one('select');
                        if (select !== null) {
                            overlay_components.push(select.get('value'));
                        }
                        else {
                            overlay_components.push(null);
                        }
                    }
                );
                return overlay_components;
            }
        }
    }
});

Y.extend(ParentSeriesListWidget, formwidgets.FormRowWidget, {

    initializer: function() {
        ParentSeriesListWidget.superclass.initializer();
        this.client = new Y.lp.client.Launchpad();
        this.clean_display();
    },

    /**
     * Display a simple message when no parent series are selected.
     *
     * @method clean_display
     */
    clean_display: function() {
        this.fieldNode.empty();
        this.fieldNode.append(Y.Node.create("<div />")
            .set('text', '[No parent for this series yet!]'));
    },

    /**
     * Display the table header.
     *
     * @method init_display
     */
    init_display: function() {
        this.fieldNode.empty();
        this.fieldNode = Y.Node.create("<table />");
        var table_header = Y.Node.create(
            ["<thead><tr>",
             "<th>Order</th>",
             "<th>Parent name</th>",
             "<th>Overlay?</th>",
             "<th>Component</th>",
             "<th>Pocket</th>",
             "<th>Delete</th>",
             "</tr></thead>",
             "<tbody>",
             "</tbody>"
            ].join(""));
        this.fieldNode.append(table_header);
    },

    /**
     * Helper method to create a select widget from a list and add it
     * to a node.
     *
     * @method build_selector
     */
    build_selector: function(node, res_list, class_name) {
        var select = Y.Node.create('<select disabled="disabled"/>');
        res_list.forEach(
            function(choice) {
                select.appendChild('<option />')
                    .set('text', choice)
                    .set('value', choice);
            });
        node.one('td.'+class_name).append(select);
        node.one('input').on('click', function(e) {
            var select = node.one('td.'+class_name).one('select');
            if (select.hasAttribute('disabled')) {
                select.removeAttribute('disabled');
            }
            else {
                select.setAttribute('disabled', 'disabled');
            }
        });
    },

    /**
     * Build a select widget from a list retrieved from the api.
     *
     * @method build_select
     */
    build_select: function(node, class_name, path) {
        var self = this;
        var on = {
            success: function(res_list) {
                self.build_selector(node, res_list, class_name);
            },
            failure: function() {
                var failed_node = Y.Node.create('<span />')
                    .set('text', 'Failed to retrieve content.');
                node.one('td.'+class_name).append(failed_node);
                self.disable_overlay(node);
            }
        };
        this.client.get(path, {on: on});
     },


    /**
     * Move down a parent's line in the table.
     *
     * @method move_down
     */
    move_down: function(parent_id) {
        var node = this.fieldNode.one("tr#parent-" + parent_id);
        var other = node.next('tr.parent');
        if (other !== null) { node.swap(other);}
        Y.lazr.anim.green_flash({node: node}).run();
    },

    /**
     * Move up a parent's line in the table.
     *
     * @method move_up
     */
    move_up: function(parent_id) {
        var node = this.fieldNode.one("tr#parent-" + parent_id);
        var other = node.previous('tr.parent');
        if (other !== null) { node.swap(other);}
        Y.lazr.anim.green_flash({node: node}).run();
    },

    /**
     * Remove a parent series.
     *
     * @method remove_parent
     */
    remove_parent: function(parent_id) {
        if (this.get('parents').length === 1) {
            this.clean_display();
            this.renderUI();
        }
        else {
            this.fieldNode.one('tr#parent-' + parent_id).remove();
        }
        Y.fire("parent_removed", parent_id);
    },

    /**
     * Disable the overlay (used when something goes wrong fetching possible
     * components or pockets for the overlay).
     *
     * @method disable_overlay
     */
    disable_overlay: function(parent_node) {
        var overlay = parent_node.one('input.overlay');
        if (overlay.get('disabled') !== 'disabled') {
            Y.lazr.anim.red_flash({node: parent_node}).run();
            parent_node.one('input.overlay').set('disabled','disabled');
        }
    },

    /**
     * Add a parent series.
     *
     * @method add_parent
     */
    add_parent: function(parent) {
        if (this.get('parents').length === 0) {
            this.init_display();
            this.renderUI();
        }
        var item = this.fieldNode.one('tr#parent-' + parent.value);
        if (item !== null) {
            Y.lazr.anim.red_flash({node: item}).run();
            return false;
        }
        item =  Y.Node.create("<tr />")
            .addClass('parent')
            .set('id', 'parent-' + parent.value)
            .append(Y.Node.create("<td />")
                .append(Y.Node.create('<a href="" title="Move parent up"/>')
                    .addClass('move-up')
                .set('innerHTML', '&uarr;'))
                .append(Y.Node.create('<a href="" title="Move parent down"/>')
                    .addClass('move-down')
                .set('innerHTML', '&darr;')))
            .append(Y.Node.create("<td />")
                .addClass('series')
                .set('text', parent.title))
            .append(Y.Node.create("<td />")
                .set('align', 'center')
                .append(Y.Node.create('<input type="checkbox" />')
                    .addClass('overlay')))
            .append(Y.Node.create("<td />")
                .addClass('component'))
            .append(Y.Node.create("<td />")
                .addClass('pocket'))
            .append(Y.Node.create("<td />")
                .set('align', 'center')
                .append(Y.Node.create('<span />')
                    .addClass('sprite')
                    .addClass('remove')));
        this.fieldNode.one('tbody').append(item);
        this.build_select(item, 'component',
            parent.api_uri + '/component_names');
        this.build_select(item, 'pocket',
            parent.api_uri + '/suite_names');
        item.one('.move-up').on('click', function(e) {
            this.move_up(parent.value);
            e.preventDefault();
            return false;
        }, this);
        item.one('.move-down').on('click', function(e) {
            this.move_down(parent.value);
            e.preventDefault();
            return false;
        }, this);
        item.one('.remove').on('click', function(e) {
            var parent_id = item.get('id').replace('parent-','');
            this.remove_parent(parent_id);
            e.preventDefault();
            return false;
        }, this);

        Y.lazr.anim.green_flash({node: item}).run();
        return true;
    }
});

namespace.ParentSeriesListWidget = ParentSeriesListWidget;


/**
 * A special form of ChoiceListWidget for choosing architecture tags.
 *
 * @class ArchitecturesChoiceListWidget
 */
var ArchitecturesChoiceListWidget;

ArchitecturesChoiceListWidget = function() {
    ArchitecturesChoiceListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesChoiceListWidget, {

    NAME: 'architecturesChoiceListWidget',

    ATTRS: {
    }

});

Y.extend(ArchitecturesChoiceListWidget, formwidgets.ChoiceListWidget, {

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
        this._distroseries = {};
        this.clean_display();
    },

    /**
     * Display a simple message when no parent series are selected.
     *
     * @method clean_display
     */
    clean_display: function() {
        this.fieldNode.empty();
        this.fieldNode.append(Y.Node.create("<div />")
            .set('text', '[No architectures to select from yet!]'));
        this.renderUI();
    },

    /**
     * Add a parent distroseries, add the architectures for this new
     * distroseries to the possible choices.
     *
     * @method add_distroseries
     * @param {Object} The distroseries to add ({value:distroseries_id),
     *     api_uri:distroseries_uri}).
     */
    add_distroseries: function(distroseries) {
        var path = distroseries.api_uri + "/architectures";
        var distroseries_id = distroseries.value;
        var self = this;
        var on = {
            success: function (results) {
                self.add_distroarchseries(distroseries_id, results);
            },
            failure: this.error_handler.getFailureHandler()
        };
        this.client.get(path, {on: on});
     },

    /**
     * Remove a parent distroseries, remove the architectures only
     * present in this parent series from the possible choices.
     *
     * @method remove_distroseries
     */
    remove_distroseries: function(distroseries_id) {
        // Compute which das is only in the distroseries to be removed.
        var arch_to_remove = [];
        var das = this._distroseries[distroseries_id];
        var i, ds, j;
        for (i=0; i<das.entries.length; i++) {
            var remove_das = true;
            var arch = das.entries[i].get('architecture_tag');
            for (ds in this._distroseries) {
                if (this._distroseries.hasOwnProperty(ds) &&
                    ds !== distroseries_id) {
                   var other_das = this._distroseries[ds];
                   for (j=0; j<other_das.entries.length; j++) {
                       var other_arch = other_das.entries[j].get(
                           'architecture_tag');
                       if (other_arch === arch) {
                           remove_das = false;
                       }
                   }
                }
            }
            if (remove_das) {
                arch_to_remove.push(arch);
            }
        }
        delete this._distroseries[distroseries_id];
        this.remove_choices(arch_to_remove);
        if (this.fieldNode.all('input').isEmpty()) {
            this.clean_display();
        }
    },

    /**
     * Add a list of distroarchseries.
     *
     * @method add_distroarchseries
     * @param {String} distroseries_id The distroarchseries id.
     * @param {Object} distroarchseries The distroarchseries object.
     */
    add_distroarchseries: function(distroseries_id, distroarchseries) {
        this._distroseries[distroseries_id] = distroarchseries;
        var choices = distroarchseries.entries.map(
            function(das) {
                return das.get("architecture_tag");
            }
        );
        this.add_choices(choices);
     }

});

namespace.ArchitecturesChoiceListWidget = ArchitecturesChoiceListWidget;


/**
 * A special form of SelectWidget for choosing packagesets.
 *
 * @class PackagesetPickerWidget
 */
var PackagesetPickerWidget;

PackagesetPickerWidget = function() {
    PackagesetPickerWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(PackagesetPickerWidget, {

    NAME: 'packagesetPickerWidget',

    ATTRS: {

        /**
         * The DistroSeries the choices in this field should
         * reflect. Takes the form of a string, e.g. "ubuntu/hoary".
         *
         * @property distroSeries
         */
        distroSeries: {
            setter: function(value, name) {
                var distro_series_uri = Y.lp.client.get_absolute_uri(value);
                var on = {
                    start: Y.bind(this.showSpinner, this),
                    success: Y.bind(this.set, this, "packageSets"),
                    failure: this.error_handler.getFailureHandler(),
                    end: Y.bind(this.hideSpinner, this)
                };
                var config = {
                    on: on,
                    parameters: {
                        distroseries: distro_series_uri
                    }
                };
                this.client.named_get("package-sets", "getBySeries", config);
            }
        }
    }
});


Y.extend(PackagesetPickerWidget, formwidgets.SelectWidget, {

    /**
     * Add a distroseries: add its packagesets to the packageset picker.
     *
     * @method add_distroseries
     * @param {Object} distroseries An object describing a
     *     distroseries, containing three properties: api_uri, title
     *     and value. The first two are what you might expect. The
     *     last is simply a unique term for referencing the
     *     distroseries which is required when calling
     *     remove_distroseries.
     */
    add_distroseries: function(distroseries) {
        var distro_series_uri = Y.lp.client.get_absolute_uri(
            distroseries.api_uri);
        var self = this;
        var on = {
            success: function (results) {
                self.add_packagesets(results, distroseries);
            },
            failure: this.error_handler.getFailureHandler()
        };
        var config = {
            on: on,
            parameters: {
                distroseries: distro_series_uri
            }
        };
        this.client.named_get("package-sets", "getBySeries", config);
    },

    /**
     * Display a simple message when no parent series are selected.
     *
     * XXX: GavinPanella 2011-07-18 bug=???: This does not remove the
     * distroseries and thus can leave the widget in an invalid state.
     *
     * @method clean_display
     */
    clean_display: function() {
        this.fieldNode.empty();
        this.fieldNode.append(Y.Node.create("<div />")
            .set('text', '[No package sets to select from yet!]'));
        this.renderUI();
    },

    /**
     * Initialize the picker's select node.
     *
     * @method init_select
     */
    init_select: function() {
        var select = this.fieldNode.one('select');
        if (select === null) {
            select = Y.Node.create("<select />");
            select.set("name", this.get("name"))
                    .set("size", this.get("size"));
            if (this.get("multiple")) {
                select.set("multiple", "multiple");
            }
            this.fieldNode.empty().append(select);
        }
        return select;
    },

    /**
     * Add a choice to the picker.
     *
     * @method add_choice
     * @param {Object} choice The choice object to be added
     *     ({text: choice_text, value: choice_value, data: choice_data}).
     */
    add_choice: function(choice) {
        var select = this.init_select();
        var option = Y.Node.create("<option />");
        option.set("value", choice.value)
            .set("text", choice.text)
            .setData("data", choice.data);
        var options = select.all('option');
        if (options.isEmpty()) {
            select.append(option);
        }
        else {
            var pos = this._sorted_position(choice.text);
            if (pos === 0) {
                select.prepend(option);
            }
            else {
                select.insertBefore(option, options.item(pos));
            }
        }
    },

    /**
     * Add choices (a set of packagesets) to the picker.
     *
     * @method add_packagesets
     * @param {Y.lp.client.Collection} packagesets The collection of
     *     packagesets to add.
     * @param {Object} distroseries The distroseries object
     *     ({value:distroseries_id), api_uri:distroseries_uri}).
     */
    add_packagesets: function(packagesets, distroseries) {
        this._packagesets[distroseries.value] = packagesets.entries;
        packagesets.entries.forEach(
            function(packageset) {
                var value = packageset.get("id");
                this.add_choice({
                    data: packageset,
                    value: value,
                    text: (
                        packageset.get("name") + ": " +
                        packageset.get("description") +
                        " (" + distroseries.title + ") ")
                });
            }, this);
        this.autoSize(10);
        Y.lazr.anim.green_flash({node: this.fieldNode}).run();
     },

    /**
     * Remove a distroseries: remove its packagesets from the picker.
     *
     * @method remove_distroseries
     * @param {String} distroseries_id The id of the distroseries to be
     *     removed.
     */
    remove_distroseries: function(distroseries_id) {
        this._packagesets[distroseries_id].forEach(
            function(packageset) {
                this.fieldNode.one(
                    'option[value="' + packageset.get("id") + '"]').remove();
            }, this);
       Y.lazr.anim.green_flash({node: this.fieldNode}).run();
        if (this.fieldNode.all('option').isEmpty()) {
            this.clean_display();
        }
    },

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
        this.clean_display();
        // _packagesets maps each distroseries' id to a collection of ids
        // of its packagesets.
        // It's populated each time a new distroseries is added as a parent
        // and used when a distroseries is removed to get all the
        // corresponding packagesets to be removed from the widget.
        this._packagesets = {};
    }

});

namespace.PackagesetPickerWidget = PackagesetPickerWidget;


}, "0.1", {"requires": [
               "node", "dom", "io", "widget", "lp.client",
               "lp.app.formwidgets", "lazr.anim", "array-extras",
               "transition"]});
