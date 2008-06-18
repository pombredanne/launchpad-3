# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'ILocationWidget',
    'LocationWidget',
    ]

from zope.interface import implements
from zope.component import getUtility
from zope.app.form import InputWidget
from zope.app.form.browser.interfaces import IBrowserWidget
from zope.app.form.browser.widget import BrowserWidget
from zope.app.form.interfaces import WidgetInputError, IInputWidget
from zope.formlib import form
from zope.schema import Choice, Float

from canonical.launchpad.webapp.interfaces import IMultiLineWidgetLayout
from canonical.launchpad.webapp.tales import ObjectImageDisplayAPI
from canonical.launchpad.interfaces import (
    IGeoIPRecord, ILaunchBag, IObjectWithLocation)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad import _


class ILocationWidget(
    IInputWidget, IBrowserWidget, IMultiLineWidgetLayout):
    """A widget for selecting a location and time zone."""


class LocationValue:
    """A location passed back from a LocationWidget.

    This is a single object which contains the latitude, longitude and time
    zone of the location.
    """
    def __init__(self, latitude, longitude, time_zone):
        self.latitude = latitude
        self.longitude = longitude
        self.time_zone = time_zone


class LocationWidget(BrowserWidget, InputWidget):
    """See `ILocationWidget`."""

    implements(ILocationWidget)

    def __init__(self, context, request):
        request.needs_json = True
        request.needs_gmap2 = True
        super(LocationWidget, self).__init__(context, request)
        fields = form.Fields(
            Float(__name__='latitude', title=_('Lat'), required=False),
            Float(__name__='longitude', title=_('Long'), required=False),
            Choice(__name__='time_zone', vocabulary='TimezoneName',
                   title=_('Time zone'), required=True))
        # This will be the initial zoom level and center of the map
        self.zoom = 2
        self.center_lat = 15.0
        self.center_long = 0.0
        # By default, we will not show a marker initially, because we are
        # not absolutely certain of the location we are proposing.  The
        # variable is a number that will be passed to JavaScript and
        # evaluated as a boolean.
        self.show_marker = 0
        data = {
            'time_zone': None,
            'latitude': None,
            'longitude': None}
        # If we are creating a record for ourselves, then we will default to
        # a location GeoIP guessed, and a higher zoom.
        if getUtility(ILaunchBag).user == context.context:
            geo_request = IGeoIPRecord(request)
            self.zoom = 7
            self.center_lat = geo_request.latitude
            self.center_long = geo_request.longitude
            data['time_zone'] = geo_request.time_zone
        current_location = IObjectWithLocation(self.context.context)
        if current_location.latitude is not None:
            # We are updating a location.
            data['latitude'] = current_location.latitude
            data['longitude'] = current_location.longitude
            self.center_lat = current_location.latitude
            self.center_long = current_location.longitude
            self.zoom = 9
            self.show_marker = 1
        if current_location.time_zone is not None:
            # We are updating a time zone.
            data['time_zone'] = current_location.time_zone
        self.initial_values = data
        widgets = form.setUpWidgets(
            fields, self.name, context, request, ignore_request=False,
            data=data)
        self.time_zone_widget = widgets['time_zone']
        self.latitude_widget = widgets['latitude']
        self.longitude_widget = widgets['longitude']

    def __call__(self):
        person = self.context.context
        person_name = person.name
        person_displayname = person.browsername
        logo_html = ObjectImageDisplayAPI(person).logo()
        latname = self.name + '.latitude'
        longname = self.name + '.longitude'
        divname = self.name.replace('.', '_') + '_div'
        mapname = divname + '_map'
        return """
    %(latitude_widget)s
    %(longitude_widget)s
    <p class="formHelp">
      Click the map to indicate a location. You can drag this
      marker, and zoom into the map to make sure it is accurate. Use
      the scroll-wheel on your mouse to zoom in and out of the map
      quickly. Double-clicking will also zoom in and move the
      marker. Please <strong>do not disclose sensitive information such
      as a specific home location</strong> without the permission of
      the person involved - rather just indicate a city so that the time
      zone is correct.
    </p>
    <p id="%(div)s"
         style="width: 100%%; height: 300px; border: 1px; float: left;"
         ></p>
    <script type="text/javascript">

    //<![CDATA[

    function setLocation(lat, lng, field_name, latname, lngname) {

        document.getElementById(latname).value = lat;
        document.getElementById(lngname).value = lng;

        var request = new JSONScriptRequest();
        var url = "%(tz_ws_url)s"+"?username=launchpad&lat="+lat.toString()+"&lng="+lng.toString();

        document.getElementById(field_name+".spinner").src = "/@@/spin";
        request.open("GET", url);

        request.onreadystatechange = function(){
          if (request.readyState == 4) {
            if (request.responseText){
              tz = request.responseJSON.timezoneId;
              document.getElementById(field_name).value = tz;
              document.getElementById(field_name+".spinner").src = "/@@/nospin";
            }
          }
        };
        request.send(null);
    }


    if (GBrowserIsCompatible()) {
        var myWidth = 0, myHeight = 0;
        if( typeof( window.innerWidth ) == 'number' ) {
          //Non-IE
          myWidth = window.innerWidth;
          myHeight = window.innerHeight;
          }
        else if( document.documentElement && (
          document.documentElement.clientWidth ||
          document.documentElement.clientHeight ) ) {
          //IE 6+ in 'standards compliant mode'
          myWidth = document.documentElement.clientWidth;
          myHeight = document.documentElement.clientHeight;
        } else if( document.body && (
              document.body.clientWidth ||
              document.body.clientHeight ) ) {
          //IE 4 compatible
          myWidth = document.body.clientWidth;
          myHeight = document.body.clientHeight;
        }
        var mapdiv = document.getElementById("%(div)s");
        var mapheight = (parseInt(mapdiv.offsetWidth) / 16 * 9);
        mapheight = Math.min(mapheight, myHeight - 180);
        mapheight = Math.max(mapheight, 400);
        mapdiv.style.height = mapheight + 'px';

        var %(map)s = new GMap2(mapdiv);
        center = new GLatLng(%(center_lat)s, %(center_long)s);
        %(map)s.setCenter(center, %(zoom)s);
        %(map)s.setMapType(G_HYBRID_MAP);
        %(map)s.addControl(new GLargeMapControl());
        %(map)s.addControl(new GMapTypeControl());
        %(map)s.addControl(new GOverviewMapControl());
        %(map)s.addControl(new GScaleControl());
        %(map)s.enableScrollWheelZoom();

        var marker = new GMarker(center, {draggable: true});
        var myHTML = '<div align="center">'
        myHTML = myHTML + '<strong>%(displayname)s</strong><br />'
        myHTML = myHTML + '%(logo_html)s<br />'
        myHTML = myHTML + '(%(name)s)'+ '</div>'
        marker.bindInfoWindowHtml(myHTML, {maxWidth: 120});

        GEvent.addListener(marker, "dragend", function() {
          point = marker.getLatLng();
          setLocation(
            point.lat(), point.lng(), "%(tz_name)s",
            "%(latname)s", "%(lngname)s");
        });

        GEvent.addListener(marker, "dragstart", function() {
          marker.closeInfoWindow();
        });

        %(map)s.addOverlay(marker);
        if (!%(show_marker)s) {
          marker.hide();
          };

        GEvent.addListener(%(map)s, "zoomend", function() {
          marker.closeInfoWindow();
          });

        GEvent.addListener(%(map)s, "click", function(overlay, point) {
          marker.setPoint(point);
          if (marker.isHidden()) {
            marker.show();
            %(map)s.panTo(point);
            };
          setLocation(
            point.lat(), point.lng(), "%(tz_name)s",
            "%(latname)s", "%(lngname)s");
         });

      }

    //]]>
    </script>

    <p>
      <label>Time zone:
      <img id="%(tz_name)s.spinner" src="/@@/nospin" width="14" height="14" />
      </label>
      %(tz_widget)s
    </p>

    <p class="formHelp">
      Once the time zone is correctly set, events in Launchpad will be
      displayed in local time.
    </p>

    """ % {
        'latitude_widget': self.latitude_widget.hidden(),
        'longitude_widget': self.longitude_widget.hidden(),
        'center_lat': self.center_lat,
        'center_long': self.center_long,
        'latname': latname,
        'lngname': longname,
        'name': person_name,
        'displayname': person_displayname,
        'logo_html': logo_html,
        'div': divname,
        'map': mapname,
        'tz_name': self.time_zone_widget.name,
        'tz_widget': self.time_zone_widget(),
        'tz_ws_url': 'http://ba-ws.geonames.net/timezoneJSON',
        'zoom': self.zoom,
        'show_marker': self.show_marker
        }

    def hasInput(self):
        return self.time_zone_widget.hasInput() or \
               self.latitude_widget.hasInput()

    def getInputValue(self):
        self._error = None
        time_zone = self.time_zone_widget.getInputValue()
        latitude = self.latitude_widget.getInputValue()
        longitude = self.longitude_widget.getInputValue()
        if time_zone is None:
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide valid time zone.')))
            raise self._error
        if (latitude is None) != (longitude is None):
            # We must receive both a latitude and a longitude.
            self._error = WidgetInputError(
                self.name, self.label,
                LaunchpadValidationError(
                    _('Please provide both latitude and longitude.')))
            raise self._error
        if latitude is not None:
            if abs(latitude) > 90 or abs(longitude) > 180:
                # We need latitude and longitude within range.
                self._error = WidgetInputError(
                    self.name, self.label, LaunchpadValidationError(
                        _('Please provide a more realistic latitude '
                          'and longitude.')))
                raise self._error
        return LocationValue(latitude, longitude, time_zone)


