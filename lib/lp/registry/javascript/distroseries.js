/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * DistroSeries related stuff.
 *
 * @module registry
 * @submodule distroseries
 */

YUI.add('lp.registry.distroseries.initseries', function(Y) {

Y.log('loading lp.registry.distroseries.initseries');

var namespace = Y.namespace('lp.registry.distroseries.initseries');


/**
 * A form row matching that which LaunchpadForm presents, containing a
 * field (defined in a subclass), and an optional label and
 * description.
 *
 * @class FormRowWidget
 */
var FormRowWidget = function() {
    FormRowWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(FormRowWidget, {

    NAME: 'formRowWidget',

    ATTRS: {

        /**
         * The field name.
         *
         * @property name
         */
        name: {
            setter: function(value, name) {
                this.fieldNode.all("input, select").set("name", value);
            }
        },

        /**
         * The top label for the field.
         *
         * @property label
         */
        label: {
            getter: function() {
                return this.labelNode.get("text");
            },
            setter: function(value, name) {
                this.labelNode.set("text", value);
            }
        },

        /**
         * A dictionary {link:link, text:text} to populate
         * the pop-up help for the field.
         *
         * @property help
         */
        help: {
            getter: function() {
                return {link:this.helpNode.one('a')
                            .get("href"),
                        text:this.helpNode
                            .one('.invisible-link')
                            .get("text")};
            },
            setter: function(value, name) {
                if ((value.link !== undefined) &&
                    (value.text !== undefined)) {
                    this.helpNode.one('a').set("href", value.link);
                    this.helpNode.one('.invisible-link')
                        .set("text", value.text);
                    this.helpNode.removeClass('unseen');
                }
                else {
                    this.helpNode.addClass('unseen');
                }
            }
        },

        /**
         * A description shown near the field.
         *
         * @label description
         */
        description: {
            getter: function() {
                return this.descriptionNode.get("text");
            },
            setter: function(value, name) {
                this.descriptionNode.set("text", value);
            }
        }
    }

});

Y.extend(FormRowWidget, Y.Widget, {

    BOUNDING_TEMPLATE: "<tr></tr>",

    CONTENT_TEMPLATE: '<td colspan="2"></td>',

    initializer: function(config) {
        this.labelNode = Y.Node.create("<label />");
        this.helpNode = Y.Node.create(('<span class="helper unseen">'+
            '&nbsp;<a href=""' +
            'target="help" class="sprite maybe">&nbsp;' +
            '<span class="invisible-link"></span></a></span>'));
        this.fieldNode = Y.Node.create("<div></div>");
        this.descriptionNode = Y.Node.create('<p class="formHelp" />');
        this.spinnerNode = Y.Node.create(
            '<img src="/@@/spinner" alt="Loading..." />');
    },

    renderUI: function() {
        this.get("contentBox")
            .append(this.labelNode)
            .append(this.helpNode)
            .append(this.fieldNode)
            .append(this.descriptionNode);
    },

    /**
     * Show the spinner.
     *
     * @method showSpinner
     */
    showSpinner: function() {
        this.fieldNode.empty().append(this.spinnerNode);
    },

    /**
     * Hide the spinner.
     *
     * @method hideSpinner
     */
    hideSpinner: function() {
        this.spinnerNode.remove();
    },

    /**
     * Display an error.
     *
     * @method showError
     */
    showError: function(error) {
        var message = Y.Node.create('<p />').set("text", error);
        this.fieldNode.empty().append(message);
        Y.lazr.anim.red_flash({node: message}).run();
    }

});

namespace.FormRowWidget = FormRowWidget;

/**
 * A table to display, order, delete the selected parent series. Each parent
 * can also be made an overlay, and a component and a pocket selected.
 *
 */
var ParentSeriesListWidget = function() {
    ParentSeriesListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ParentSeriesListWidget, {

    NAME: 'parentSeriesListWidget',

    ATTRS: {

        parentSeries: {
            getter: function() {
                var series = [];
                this.fieldNode.all("tbody > tr > td.series").each(
                    function(node) {
                        series.push(node.get("text"));
                    }
                );
                return series;
            }
        },
        /**
         * The DistroSeries the choices in this field should
         * reflect. Takes the form of a string, e.g. "ubuntu/hoary".
         *
         * @property distroSeries
         */
        distroSeries: {
            setter: function(value, name) {
                var path = value + "/architectures";
                var on = {
                    start: Y.bind(this.showSpinner, this),
                    success: Y.bind(this.set, this, "distroArchSerieses"),
                    failure: this.error_handler.getFailureHandler(),
                    end: Y.bind(this.hideSpinner, this)
                };
                this.client.get(path, {on: on});
            }
        }
    }

});

Y.extend(ParentSeriesListWidget, FormRowWidget, {

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
        this.fieldNode = Y.Node.create("<div />")
            .set('text', '[No parent for this series yet!]');
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
             "</tbody>",
            ].join(""));
        this.fieldNode.append(table_header);
    },

    /**
     * Build a select widget from a list retrieved from the api.
     *
     * @method build_select
     */
    build_select: function(node, class_name, path) {
        var on = {
            success: function(res_list) {
                var select = Y.Node.create('<select disabled="disabled"/>')
                res_list.forEach(
                    function(choice) {
                        select.appendChild('<option />').set('text', choice)
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
            failure: function() {
                var failed_node = Y.Node.create('<span />')
                    .set('text', 'Failed to retrieve content.');
                node.one('td.'+class_name).append(failed_node);
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
        if (other != null) { node.swap(other);}
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
        if (other != null) { node.swap(other);}
        Y.lazr.anim.green_flash({node: node}).run();
    },

    /**
     * Add a parent series.
     *
     * @method add_parent
     */
    add_parent: function(parent) {
        if (this.get('parentSeries').length == 0) {
            this.init_display();
            this.renderUI();
        }
        var item = this.fieldNode.one('tr#parent-' + parent.value);
        if (item != null) {
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
                .append(Y.Node.create('<input type="checkbox" />')))
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
            if (this.get('parentSeries').length == 1) {
                this.clean_display();
            }
            else {
                item.remove();
            }
            if (this.get('parentSeries').length == 0) {
                this.clean_display();
                this.renderUI();
            }
            Y.fire("parent_removed", item.get('id').replace('parent-',''));
            e.preventDefault();
            return false;
        }, this);

        Y.lazr.anim.green_flash({node: item}).run();
        return true;
    }
});

namespace.ParentSeriesListWidget = ParentSeriesListWidget;


/**
 * A form row matching that which LaunchpadForm presents, containing a
 * list of checkboxes, and an optional label and description.
 *
 * @class ChoiceListWidget
 */
var ChoiceListWidget = function() {
    ChoiceListWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(ChoiceListWidget, {

    NAME: 'choiceListWidget',

    ATTRS: {

        /**
         * An array of strings from which to choose.
         *
         * @property choices
         */
        choices: {
            getter: function() {
                return this.fieldNode.all("li > input").get("value");
            },
            setter: function(value, name) {
                var choices = Y.Array.unique(value).sort();
                var list = Y.Node.create("<ul />");
                var self = this;
                choices.forEach(
                    function(choice) {
                       var item = self._createChoice(choice);
                       list.append(item);
                    }
                );
                this.fieldNode.empty().append(list);
            }
        },

        /**
         * The current selection.
         *
         * @property choice
         */
        choice: {
            setter: function(value, name) {
                if (!Y.Lang.isArray(value)) {
                    value = [value];
                }
                this.fieldNode.all("li > input").each(
                    function(node) {
                        node.set(
                            "checked",
                            value.indexOf(node.get("value")) >= 0);
                    }
                );
            },
            getter: function() {
                var choice = [];
                this.fieldNode.all("li > input").each(
                    function(node) {
                        if (node.get("checked")) {
                            choice.push(node.get("value"));
                        }
                    }
                );
                if (this.get("type") == "radio") {
                    if (choice.length === 0) {
                        choice = null;
                    }
                    else if (choice.length == 1) {
                        choice = choice[0];
                    }
                    else {
                        choice = undefined;
                    }
                }
                return choice;
            }
        },

        /**
         * The input type to display. Choose from "checkbox" or "radio".
         *
         * @property type
         */
        type: {
            value: "checkbox",
            setter: function(value, name) {
                this.fieldNode.all("li > input").set("type", value);
            }
        }

    }

});

Y.extend(ChoiceListWidget, FormRowWidget, {

    /**
     * Helper method to create an entry for the select widget.
     *
     * @method _createChoice
     */
    _createChoice: function(choice, field_type, field_name) {
         var field_name = this.get("name");
         var field_type = this.get("type");
         var item = Y.Node.create(
            "<li><input /> <label /></li>");
        item.one("input")
            .set("type", field_type)
            .set("name", field_name)
            .set("value", choice);
        item.one("label")
            .setAttribute(
                "for", item.one("input").generateID())
            .setStyle("font-weight", "normal")
            .set("text", choice);
        return item;
    },

   /**
     * Remove a list of choices from the possible widget's choices.
     *
     * @method remove_choices
     */
    remove_choices: function(choices) {
        choices.forEach(
            function(choice) {
                this.fieldNode.all("select > option").each(
                    function(option) { options.push(option); });
                this.fieldNode.all(
                    "li input[value=" + choice + "]").each(
                        function(li_element) {
                            li_element.get('parentNode').remove();
                        }
                );
            },
            this
        );
        Y.lazr.anim.green_flash({node: this.fieldNode}).run();
     },

    /**
     * Add new choices (if they are not already present).
     *
     * @method add_choices
     */
    add_choices: function(new_choices) {
        new_choices.forEach(
            function(choice) {
                if (this.fieldNode.all(
                    "li > input[value=" + choice + "]").isEmpty()) {
                    var list = this.fieldNode.one('ul');
                    if (list == null) {
                        var list = Y.Node.create("<ul />");
                        this.fieldNode.empty().append(list);
                    }
                    list.append(this._createChoice(choice));
                }
            }, this
        );
        Y.lazr.anim.green_flash({node: this.fieldNode}).run();
    }

});


namespace.ChoiceListWidget = ChoiceListWidget;


/**
 * A special form of ChoiceListWidget for choosing architecture tags.
 *
 * @class ArchitecturesChoiceListWidget
 */
var ArchitecturesChoiceListWidget = function() {
    ArchitecturesChoiceListWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesChoiceListWidget, {

    NAME: 'architecturesChoiceListWidget',

    ATTRS: {
    }

});

Y.extend(ArchitecturesChoiceListWidget, ChoiceListWidget, {

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
        this.fieldNode = Y.Node.create("<div />")
            .set('text', '[No architectures to select from yet!]');
        this.renderUI();
    },

    /**
     * Add a parent distroseries, add the architectures for this new
     * distroseries to the possible choices.
     *
     * @method add_distroseries
     */
    add_distroseries: function(distroseries) {
        var path = distroseries.api_uri + "/architectures";
        var distroseries_id = distroseries.value;
        var self = this;
        var on = {
            success: function (results) {
                self.add_distroarchseries(distroseries_id, results);
            },
            failure: this.error_handler.getFailureHandler(),
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
        arch_to_remove = []
        var das = this._distroseries[distroseries_id];
        for (i=0; i<das.entries.length; i++) {
            remove_das = true;
            arch = das.entries[i].get('architecture_tag');
            for (var ds in this._distroseries) {
                if (ds !== distroseries_id) {
                   var other_das = this._distroseries[ds];
                   for (j=0; j<other_das.entries.length; j++) {
                       var other_arch = other_das.entries[j].get(
                           'architecture_tag');
                       if (other_arch == arch) {
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
 * A special form of FormRowWidget, containing a select control.
 *
 * @class SelectWidget
 */
var SelectWidget = function() {
    SelectWidget.superclass.constructor.apply(this, arguments);
};

Y.mix(SelectWidget, {

    NAME: 'selectWidget',

    ATTRS: {

        /**
         * An array of objects from which to choose. Each object
         * should contain a value for "value", "text" and "data".
         *
         * @property choices
         */
        choices: {
            getter: function() {
                /* I think this is a YUI3 wart; I can't see any way to
                   map() over a NodeList, so I must push the elements
                   one by one into an array first. */
                var options = Y.Array([]);
                this.fieldNode.all("select > option").each(
                    function(option) { options.push(option); });
                return options.map(
                    function(option) {
                        return {
                            value: option.get("value"),
                            text: option.get("text"),
                            data: option.getData("data")
                        };
                    }
                );
            },
            setter: function(value, name) {
                var select = Y.Node.create("<select />");
                select.set("name", this.get("name"))
                      .set("size", this.get("size"));
                if (this.get("multiple")) {
                    select.set("multiple", "multiple");
                }
                var choices = Y.Array(value);
                choices.forEach(
                    function(choice) {
                        var option = Y.Node.create("<option />");
                        option.set("value", choice.value)
                              .set("text", choice.text)
                              .setData("data", choice.data);
                        select.append(option);
                    }
                );
                if (choices.length > 0) {
                    this.fieldNode.empty().append(select);
                }
                else {
                    this.fieldNode.empty();
                }
            }
        },

        /**
         * The current selection.
         *
         * @property choice
         */
        choice: {
            setter: function(value, name) {
                if (!Y.Lang.isArray(value)) {
                    value = [value];
                }
                this.fieldNode.all("select > option").each(
                    function(node) {
                        node.set(
                            "selected",
                            value.indexOf(node.get("value")) >= 0);
                    }
                );
            },
            getter: function() {
                var choice = [];
                this.fieldNode.all("select > option").each(
                    function(node) {
                        if (node.get("selected")) {
                            choice.push(node.get("value"));
                        }
                    }
                );
                return choice;
            }
        },

        /**
         * The number of rows to show in the select widget.
         *
         * @property size
         */
        size: {
            value: 1,
            setter: function(value, name) {
                this.fieldNode.all("select").set("size", value);
            }
        },

        /**
         * Whether multiple rows can be selected.
         *
         * @property multiple
         */
        multiple: {
            value: false,
            setter: function(value, name) {
                value = value ? true : false;
                this.fieldNode.all("select").set("multiple", value);
                return value;
            }
        }

    }

});

Y.extend(SelectWidget, FormRowWidget, {

    /**
     * Add a choice to the picker.
     *
     * @method add_choice
     */
    add_choice: function(choice) {
        var select = this.init_select();
        var option = Y.Node.create("<option />");
        option.set("value", choice.value)
                .set("text", choice.text)
                .setData("data", choice.data);
        select.append(option);
    },

    /**
     * Choose a size for the select control based on the number of
     * choices, up to an optional maximum size.
     *
     * @method autoSize
     */
    autoSize: function(maxSize) {
        var choiceCount = this.fieldNode.all("select > option").size();
        if (choiceCount === 0) {
            this.set("size", 1);
        }
        else if (maxSize === undefined) {
            this.set("size", choiceCount);
        }
        else if (choiceCount < maxSize) {
            this.set("size", choiceCount);
        }
        else {
            this.set("size", maxSize);
        }
        return this;
    }

});

namespace.SelectWidget = SelectWidget;


/**
 * A special form of SelectWidget for choosing packagesets.
 *
 * @class PackagesetPickerWidget
 */
var PackagesetPickerWidget = function() {
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


Y.extend(PackagesetPickerWidget, SelectWidget, {

    /**
     * Add a distroseries: add it's packagesets to the packageset picker.
     *
     * @method add_distroseries
     */
    add_distroseries: function(distroseries) {
        var distro_series_uri = Y.lp.client.get_absolute_uri(distroseries.api_uri);
        var self = this;
        var on = {
            success: function (results) {
                self.add_packagesets(results, distroseries);
            },
            failure: this.error_handler.getFailureHandler(),
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
     * @method clean_display
     */
    clean_display: function() {
        this.fieldNode.empty();
        this.fieldNode = Y.Node.create("<div />")
            .set('text', '[No package sets to select from yet!]');
        this.renderUI();
    },

    /**
     * Initialise the picket's select node.
     *
     * @method init_select
     */
    init_select: function() {
        var select = this.fieldNode.one('select');
        if (select == null) {
            var select = Y.Node.create("<select />");
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
     * Add choices (a set of packagesets) to the picker.
     *
     * @method add_packagesets
     */
    add_packagesets: function(packagesets, distroseries) {
        packagesets.entries.forEach(
            function(packageset) {
                var value = packageset.get("name")+'-'+distroseries.value;
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
     * Remove a distroseries: remove it's packagesets from the picker.
     *
     * @method remove_distroseries
     */
    remove_distroseries: function(distroseries_id) {
        this.fieldNode.all(
            'option[value$="\-' + distroseries_id + '"]').remove();
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
    }

});

namespace.PackagesetPickerWidget = PackagesetPickerWidget;


/**
 * A widget to encapsulate functionality around the form actions.
 *
 * @class FormActionsWidget
 */
var FormActionsWidget = function() {
    FormActionsWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(FormActionsWidget, {

    NAME: 'formActionsWidget',

    HTML_PARSER: {
        submitButtonNode: "input[type=submit]"
    }

});

Y.extend(FormActionsWidget, Y.Widget, {

    initializer: function(config) {
        this.client = new Y.lp.client.Launchpad();
        this.error_handler = new Y.lp.client.ErrorHandler();
        this.error_handler.clearProgressUI = Y.bind(this.hideSpinner, this);
        this.error_handler.showError = Y.bind(this.showError, this);
        this.submitButtonNode = config.submitButtonNode;
        this.spinnerNode = Y.Node.create(
            '<img src="/@@/spinner" alt="Loading..." />');
    },

    /**
     * Show the spinner, and hide the submit button.
     *
     * @method showSpinner
     */
    showSpinner: function() {
        this.submitButtonNode.replace(this.spinnerNode);
    },

    /**
     * Hide the spinner, and show the submit button again.
     *
     * @method hideSpinner
     */
    hideSpinner: function() {
        this.spinnerNode.replace(this.submitButtonNode);
    },

    /**
     * Display an error.
     *
     * @method showError
     */
    showError: function(error) {
        Y.Node.create('<p class="error message" />')
            .appendTo(this.get("contentBox"))
            .set("text", error);
    },

    /**
     * Remove all errors that have been previously displayed by showError.
     *
     * @method hideErrors
     */
    hideErrors: function(error) {
        this.get("contentBox").all("p.error.message").remove();
    }

});

namespace.FormActionsWidget = FormActionsWidget;


/**
 * A widget to encapsulate functionality around the form actions.
 *
 * @class DeriveDistroSeriesActionsWidget
 */
var DeriveDistroSeriesActionsWidget = function() {
    DeriveDistroSeriesActionsWidget
        .superclass.constructor.apply(this, arguments);
};

Y.mix(DeriveDistroSeriesActionsWidget, {

    NAME: 'deriveDistroSeriesActionsWidget'

});

Y.extend(DeriveDistroSeriesActionsWidget, FormActionsWidget, {

    initializer: function(config) {
        this.context = config.context;
        this.deriveFromChoice = config.deriveFromChoice;
        this.architectureChoice = config.architectureChoice;
        this.packagesetChoice = config.packagesetChoice;
        this.packageCopyOptions = config.packageCopyOptions;
    },

    /**
     * Display a success message then fade out and remove the form.
     *
     * @method success
     */
    success: function() {
        var message = [
            "The initialization of ", this.context.displayname,
            " has been scheduled and should run shortly."
        ].join("");
        var messageNode = Y.Node.create("<p />")
            .addClass("informational")
            .addClass("message")
            .set("text", message);
        var form = this.get("contentBox").ancestor("form");
        form.transition(
            {duration: 1, height: 0, opacity: 0},
            function() { form.remove(true); });
        form.insert(messageNode, "after");
    },

    /**
     * Call deriveDistroSeries via the API.
     *
     * @method submit
     */
    submit: function() {
        var self = this;
        var config = {
            on: {
                start: function() {
                    self.hideErrors();
                    self.showSpinner();
                },
                success: Y.bind(this.success, this),
                failure: this.error_handler.getFailureHandler(),
                end: Y.bind(this.hideSpinner, this)
            },
            parameters: {
                name: this.context.name,
                distribution: this.context.distribution_link,
                architectures: this.architectureChoice.get("choice"),
                packagesets: this.packagesetChoice.get("choice"),
                rebuild: this.packageCopyOptions.get("choice") == (
                    "Copy Source and Rebuild")
            }
        };
        var parent = this.deriveFromChoice.get("value");
        this.client.named_post(
            parent, "deriveDistroSeries", config);
    }

});

namespace.DeriveDistroSeriesActionsWidget = DeriveDistroSeriesActionsWidget;

/*
 * Show the "Add parent series" overlay.
 */
var show_add_parent_series_form = function(e) {

    e.preventDefault();
    var config = {
        header: 'Add a parent series',
        step_title: 'Search'
    };

    config.save = function(result) {
        add_parent_series(result);
    };

    parent_picker = Y.lp.app.picker.create('DistroSeriesDerivation', config);
    parent_picker.show();
};

namespace.show_add_parent_series_form = show_add_parent_series_form;

/*
 * Add a parent series.
 */
var add_parent_series = function(parent) {
    Y.fire("add_parent", parent);
};

namespace.add_parent_series = add_parent_series;


/**
 * Setup the widgets on the +initseries page.
 *
 * @function setup
 */
namespace.setup = function() {
    var form_container = Y.one("#initseries-form-container");
    var form_table = form_container.one("table.form");
    var form_table_body = form_table.append(Y.Node.create('<tbody />'));

    // Widgets.
    var add_parent_link = Y.Node.create('<a href="+add-parent-series">')
            .addClass("sprite")
            .addClass("add")
            .set("id", "add-parent-series")
            .set("text", "Add parent series")
    add_parent_link.appendTo(form_table_body);
    var parents_selection =
        new ParentSeriesListWidget()
            .set("name", "field.parent")
            .set("label", "Parent Series:")
            .set("description", (
                     "Choose and configure the parent series."))
            .render(form_table_body);
    var architecture_choice =
        new ArchitecturesChoiceListWidget()
            .set("name", "field.architectures")
            .set("label", "Architectures:")
            .set("description", (
                     "Choose the architectures you want to " +
                     "use from the parent series."))
            .render(form_table_body);
    var packageset_choice =
        new PackagesetPickerWidget()
            .set("name", "field.packagesets")
            .set("size", 5)
            .set("help", {link: '/+help/init-series-packageset-help.html',
                          text: 'Packagesets help'})
            .set("multiple", true)
            .set("label", "Package sets to copy from parent:")
            .set("description", (
                     "The package sets that will be imported " +
                     "into the derived distroseries."))
            .render(form_table_body);
    var package_copy_options =
        new ChoiceListWidget()
            .set("name", "field.package_copy_options")
            .set("type", "radio")
            .set("label", "Copy options:")
            .set("description", (
                     "Choose whether to rebuild all the sources you copy " +
                     "from the parent, or to copy their binaries too."))
            .set("choices", ["Copy Source and Rebuild",
                             "Copy Source and Binaries"])
            .set("choice", "Copy Source and Binaries")
            .render(form_table_body);
    var form_actions =
        new DeriveDistroSeriesActionsWidget({
            context: LP.cache.context,
            srcNode: form_container.one("div.actions"),
            deriveFromChoice: parents_selection,
            architectureChoice: architecture_choice,
            packagesetChoice: packageset_choice,
            packageCopyOptions: package_copy_options
        });

    // Wire up the add parent series link.
    var link = Y.one('#add-parent-series');
    if (Y.Lang.isValue(link)) {
        link.addClass('js-action');
        link.on('click', show_add_parent_series_form);
    }

    Y.on('add_parent', function(parent) {
        var added = parents_selection.add_parent(parent);
        if (added) {
            Y.fire("parent_added", parent);
        }
    });

    Y.on('parent_added', function(parent) {
        architecture_choice.add_distroseries(parent);
        packageset_choice.add_distroseries(parent);
    });

    Y.on('parent_removed', function(parent_id) {
        architecture_choice.remove_distroseries(parent_id);
        packageset_choice.remove_distroseries(parent_id);
    });

    // Wire up the form submission.
    form_container.one("form").on(
        "submit", function(event) {
            event.halt(); form_actions.submit(); });

    // Show the form.
    form_container.removeClass("unseen");
};


}, "0.1", {"requires": ["node", "dom", "io", "widget", "lp.client",
                        "lazr.anim", "array-extras", "transition",
                        "lp.app.picker"]});
