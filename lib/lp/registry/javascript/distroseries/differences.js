/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * DistroSeries Initialization.
 *
 * @module lp.registry.distroseries
 * @submodule differences
 */

YUI.add('lp.registry.distroseries.differences', function(Y) {

Y.log('loading lp.registry.distroseries.differences');

var namespace = Y.namespace('lp.registry.distroseries.differences');

var widgets = Y.lp.registry.distroseries.widgets;
var formwidgets = Y.lp.app.formwidgets;


var setupPackageSetPicker = function() {
    var packagesets_headers = Y.all("th.package-sets");
    Y.each(packagesets_headers, function(packagesets_header) {
        /* XXX: GavinPanella 2011-07-19 bug=???:
           PackagesetPickerWidget needs to render into a
           container. This should not be required. */
        var packageset_picker_table =
            Y.Node.create("<table><tbody /></table>");
        var packageset_picker =
            new widgets.PackagesetPickerWidget()
                .set("name", "field.packagesets")
                .set("size", 5)
                .set("multiple", true)
                .render(packageset_picker_table.one("tbody"));
        /* XXX: GavinPanella 2011-07-19 bug=???:
           PackagesetPickerWidget.add_distroseries() accepts only this
           odd-looking object. It would be more convenient and less
           surprising if it also accepted an lp.client.Entry. */
        packageset_picker.add_distroseries({
            api_uri: LP.cache.context.self_link,
            title: LP.cache.context.title,
            value: LP.cache.context.self_link
        });
        /* Buttons */
        var submit_button = Y.Node.create(
            '<button type="submit" class="lazr-pos lazr-btn" />')
               .set("text", "OK");
        var cancel_button = Y.Node.create(
            '<button type="button" class="lazr-neg lazr-btn" />')
               .set("text", "Cancel");
        /* Form overlay. */
        var overlay = new Y.lazr.FormOverlay({
            align: {
                /* Align the top-centre of the overlay with the
                   bottom-centre of the invoking object (i.e. the
                   header cell). */
                node: packagesets_header,
                points: [
                    Y.WidgetPositionAlign.TC,
                    Y.WidgetPositionAlign.BC
                ]
            },
            headerContent: "<h2>Select package sets</h2>",
            form_content: packageset_picker_table,
            form_submit_button: submit_button,
            form_cancel_button: cancel_button,
            visible: false
        });
        /* This will render hidden but ready for use. */
        overlay.render();
        /* Show the overlay when the packagesets header is clicked. */
        packagesets_header.on("click", function(event) {
            /* Trigger alignment and constrain to the viewport. Should
               these not happen automatically? Perhaps there's a bad
               interaction between widget-position-align and
               widget-position-constrain? */
            overlay.set("align", overlay.get("align"));
            overlay.constrain(null, true);
            overlay.show();
        });

        // XXX: For Development Only.
        window.overlay = overlay;
        window.picker = packageset_picker;
    });
};


// Exports.
namespace.setupPackageSetPicker = setupPackageSetPicker;


}, "0.1", {
    "requires": [
        "dom",
        "node",
        "transition",
        "lazr.formoverlay",
        "lp.app.formwidgets",
        "lp.app.picker",
        "lp.registry.distroseries.widgets"
    ]});
