/* Copyright 2010 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Distroseries related stuff.
 *
 * @module Y.lp.registry.distroseries
 * @requires node, DOM
 */
YUI.add('lp.registry.distroseries.initseries', function(Y) {

Y.log('loading lp.registry.distroseries.initseries');

var namespace = Y.namespace('lp.registry.distroseries.initseries');

var widget_row = function(label, field, description) {
    var row = Y.Node.create(
        '<tr><td colspan="2"><div /></td></tr>');
    var div = row.one("div");
    // The label, if supplied.
    if (label !== undefined) {
        var label_node = Y.Node.create("<label />");
        label_node.set("for", field.get("name"));
        label_node.set("text", label);
        div.append(label_node);
    }
    // The field itself.
    var field_div = Y.Node.create("<div />");
    field_div.append(field);
    div.append(field_div);
    // The description, if supplied.
    if (description !== undefined) {
        var description_node = Y.Node.create("<p />");
        description_node.set("class", "formHelp");
        description_node.set("text", description);
        div.append(description_node);
    }
    return row;
};

var ArchitecturesChoice = function() {
    ArchitecturesChoice.superclass.constructor.apply(this, arguments);
};

Y.mix(ArchitecturesChoice, {

    NAME: 'architecturesChoice',

    ATTRS: {
        formTable: {writeOnce: true}
    },

});

Y.extend(ArchitecturesChoice, Y.Widget, {

    BOUNDING_TEMPLATE: (
        '<tr><td colspan="2"><div /></td></tr>'),

    CONTENT_TEMPLATE: null,

    /**
     * Implementation of Widget.renderUI.
     *
     * This adds the widget row to the form table.
     *
     * @method renderUI
     */
    renderUI: function() {
        var checkbox = Y.Node.create("<input />");
        checkbox.set("type", "checkbox");
        checkbox.set("name", "field.architectures");
        checkbox.set("value", "i386");
        var row = widget_row("Architectures", checkbox);
        var checkbox_div = checkbox.ancestor("div");
        checkbox_div.append("i386");
        this.get("boundingBox").one("div").append(row);
    }

});

namespace.ArchitecturesChoice = ArchitecturesChoice;

namespace.setup = function() {
    var form_table = Y.one(
        "[name=field.derived_from_series]").ancestor("tbody");
    var architecture_choice = new namespace.ArchitecturesChoice();
    //architecture_choice.set("formTable", form_table);
    architecture_choice.render(form_table);
};

}, "0.1", {"requires": ["node", "dom", "io", "widget"]});
