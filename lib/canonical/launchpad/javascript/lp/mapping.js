YUI.add('lp.mapping', function(Y) {
    var mapping = Y.namespace('lp.mapping');

    // jslint does not like functions that look like classes.
    var gBrowserIsCompatible = GBrowserIsCompatible;
    var gDownloadUrl = GDownloadUrl;

    /**
     * Add a marker for each participant.
     *
     * @function setMarkersInfoWindow
     * @param {String} data the participant XML.
     * @param {GMap2} map the Google map to add the markers to.
     * @param {GLatLngBounds} required_bounds the boundaries or null.
     */
    mapping.setMarkersInfoWindow = function(data, map, required_bounds) {
        var xml = GXml.parse(data);
        var markers = xml.documentElement.getElementsByTagName("participant");
        var participant = null;

        function attrToProp(attr) {
            participant[attr.name] = attr.value;
        }

        for (var i = 0; i < markers.length; i++) {
            participant = {};
            Y.Array.each(markers[i].attributes, attrToProp);
            var point = new GLatLng(
                parseFloat(participant.lat), parseFloat(participant.lng));
            if (required_bounds) {
                required_bounds.extend(point);
            }
            var marker = new GMarker(point);
            marker.bindInfoWindowHtml(Y.substitute(
                '<div style="text-align: center">' +
                '<a href="{url}">{displayname} ({name})</a><br />' +
                '{logo_html}<br />' +
                'Local time: {local_time}</div>',
                participant));
            map.addOverlay(marker);
        }
    };

    /**
     * Add a marker for each participant and update the zoom level.
     *
     * @function setMarkersInfoWindowForSmallMap
     * @param {String} data the participant XML.
     * @param {GMap2} map the Google map to add the markers to.
     */
    mapping.setMarkersInfoWindowForSmallMap = function(data, map) {
        var required_bounds = new GLatLngBounds();
        mapping.setMarkersInfoWindow(data, map, required_bounds);
        var zoom_level = map.getBoundsZoomLevel(required_bounds);
        // Some browsers do not display the map when the zoom_level is at the
        // end of the range, reduce the zoom_level by 1.
        zoom_level = Math.min(4, zoom_level - 1);
        map.setZoom(zoom_level);
    };

    /**
     * Set the timezone field to the lat-log location.
     *
     * @function setLocation
     * @param {Number} lat a GLatLng.lat bounded number.
     * @param {Number} lng a GLatLng.lng bounded number.
     * @param {String} tz_name the id of the timezone field.
     * @param {String} lat_name the id of the latitude field.
     * @param {String} lng_name the id of the longitude field.
     */
    mapping.setLocation = function(lat, lng, tz_name, lat_name, lng_name) {
        Y.get(Y.DOM.byId(lat_name)).set('value', lat);
        Y.get(Y.DOM.byId(lng_name)).set('value', lng);
        var spinner = Y.get('#tz_spinner');
        spinner.set('src', '/@@/spinner');

        function succeeded() {
            if (request.readyState == 4) {
                if (request.responseText) {
                    var tz = request.responseJSON.timezoneId;
                    Y.get(Y.DOM.byId(tz_name)).set('value', tz);
                    spinner.set('src', '/@@/nospin');
                }
            }
        }

        var url = 'http://ba-ws.geonames.net/timezoneJSON' +
            '?username=launchpad&lat=' + lat + '&lng=' + lng;
        // This is a cross-site script request.
        var request = new JSONScriptRequest();
        request.open("GET", url);
        request.onreadystatechange = succeeded;
        request.send(null);
    };

    /**
     * Create a small map with the launchpad default configuration.
     *
     * @function getSmallMap
     * @param {String} div_id the id of the map div.
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     * @return {GMap2} the Google map
     */
    mapping.getSmallMap = function(div_id, center_lat, center_lng) {
        var mapdiv = Y.DOM.byId(div_id);
        mapdiv.style.width = '400px';
        var map = new GMap2(mapdiv);
        var center = new GLatLng(center_lat, center_lng);
        map.setCenter(center, 1);
        map.setMapType(G_NORMAL_MAP);
        map.enableScrollWheelZoom();
        return map;
    };

    /**
     * Create a small map of where a person is located.
     *
     * @function renderPersonMapSmall
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    mapping.renderPersonMapSmall = function(center_lat, center_lng) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var map = mapping.getSmallMap(
            'person_map_div', center_lat, center_lng);
        map.addControl(new GSmallZoomControl());
        var center = new GLatLng(center_lat, center_lng);
        var marker = new GMarker(center);
        map.addOverlay(marker);
    };

    /**
     * Create a small map of where a team's members are located.
     *
     * @function renderTeamMapSmall
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    mapping.renderTeamMapSmall = function(center_lat, center_lng) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var team_map = mapping.getSmallMap(
            'team_map_div', center_lat, center_lng);
        gDownloadUrl("+mapdata", function(data) {
            mapping.setMarkersInfoWindowForSmallMap(data, team_map);
            });
    };

    /**
     * Create a large map with the launchpad default configuration.
     *
     * @function getLargeMap
     * @param {String} div_id the id of the map div.
     * @return {GMap2} The Google map
     */
    mapping.getLargeMap = function(div_id) {
        var mapdiv = Y.DOM.byId(div_id);
        var mapheight = (parseInt(mapdiv.offsetWidth, 10) / 16 * 9);
        mapheight = Math.min(mapheight, Y.DOM.winHeight() - 180);
        mapheight = Math.max(mapheight, 400);
        mapdiv.style.height = mapheight + 'px';
        var map = new GMap2(mapdiv);
        map.setMapType(G_HYBRID_MAP);
        map.addControl(new GLargeMapControl());
        map.addControl(new GMapTypeControl());
        map.addControl(new GOverviewMapControl());
        map.addControl(new GScaleControl());
        map.enableScrollWheelZoom();
        return map;
    };

    /**
     * Create a large map of where a team's members are located.
     *
     * @function renderTeamMap
     * @param {Number} min_lat the minimum GLatLng.lat bounded number.
     * @param {Number} max_lat the maximum GLatLng.lat bounded number.
     * @param {Number} min_lng the minimum GLatLng.lng bounded number.
     * @param {Number} max_lng the maximum GLatLng.lng bounded number.
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     */
    mapping.renderTeamMap = function(min_lat, max_lat, min_lng, max_lng,
                                     center_lat, center_lng) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var team_map = mapping.getLargeMap("team_map_div");
        var center = new GLatLng(center_lat, center_lng);
        team_map.setCenter(center, 0);
        var sw = new GLatLng(min_lat, min_lng);
        var ne = new GLatLng(max_lat, max_lng);
        var required_bounds = new GLatLngBounds(sw, ne);
        var zoom_level = team_map.getBoundsZoomLevel(required_bounds);
        // Some browsers do not display the map when the zoom_level is at
        // the end of the range, reduce the zoom_level by 1.
        zoom_level = Math.min(
            G_HYBRID_MAP.getMaximumResolution(), zoom_level - 1);
        team_map.setZoom(zoom_level);
        gDownloadUrl("+mapdata", function(data) {
            mapping.setMarkersInfoWindow(data, team_map);
            });
    };

    /**
     * Create a large, markable map of where a person is located.
     *
     * @function renderPersonMap
     * @param {Number} center_lat a GLatLng.lat bounded number.
     * @param {Number} center_lng a GLatLng.lng bounded number.
     * @param {String} displayname the user's display name.
     * @param {String} name the user's launchpad id.
     * @param {String} logo_html XXX
     * @param {String} tz_name the id of the timezone field.
     * @param {String} lat_name the id of the latitude field.
     * @param {String} lng_name the id of the longitude field.
     * @param {number} zoom the initial zoom-level.
     * @param {Boolean} show_marker Show the marker for the person.
     */
    mapping.renderPersonMap = function(center_lat, center_lng, displayname,
                                       name, logo_html, lat_name, lng_name,
                                       tz_name, zoom, show_marker) {
        if (!gBrowserIsCompatible()) {
            return;
        }
        var map = mapping.getLargeMap('map_div');
        var center = new GLatLng(center_lat, center_lng);
        map.setCenter(center, zoom);
        var marker = new GMarker(center, {draggable: true});
        marker.bindInfoWindowHtml(Y.substitute(
            '<div style="text-align: center">' +
            '<strong>{displayname}</strong><br />' +
            '{logo_html}<br />({name})</div>',
            {displayname: displayname, logo_html: logo_html, name: name}),
            {maxWidth: 120});

        GEvent.addListener(marker, "dragend", function() {
            var point = marker.getLatLng();
            mapping.setLocation(
                point.lat(), point.lng(), tz_name, lat_name, lng_name);
        });

        GEvent.addListener(marker, "dragstart", function() {
            marker.closeInfoWindow();
        });

        map.addOverlay(marker);
        if (!show_marker) {
            marker.hide();
        }

        GEvent.addListener(map, "zoomend", function() {
            marker.closeInfoWindow();
        });

        GEvent.addListener(map, "click", function(overlay, point) {
            marker.setPoint(point);
            if (marker.isHidden()) {
                marker.show();
                map.panTo(point);
            }
            mapping.setLocation(
                point.lat(), point.lng(), tz_name, lat_name, lng_name);
        });
    };
}, '0.1', {requires:['node', 'dom', 'substitute']});
