/* Copyright 2009 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/


/* A GMap-management object.  Simplifies viewpoint and marker geocoding. */
SimpleMap = function(div) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  this.div_ = div;
  this.defaultZoom_ = 10;

  this.map = new GMap2(div);

  var lat = 40, lon = -100, zoom = 3;
  try {
    lat = google.loader.ClientLocation.latitude;
    lon = google.loader.ClientLocation.longitude;
    zoom = this.defaultZoom_;
  } catch (err) {}

  this.map.setCenter(new GLatLng(lat, lon), zoom);
  this.map.enableContinuousZoom();
  this.geocoder_ = new GClientGeocoder();
  this.map.addControl(new GSmallZoomControl());

  var icon = new GIcon();
  icon.image = 'http://www.google.com/mapfiles/marker_midblue.png';
  icon.shadow = 'http://www.google.com/mapfiles/shadow-mid.png';
  icon.iconSize = new GSize(16, 27);
  icon.shadowSize = new GSize(16, 28);
  icon.iconAnchor = new GPoint(8, 27);
  icon.infoWindowAnchor = new GPoint(5, 1);
  this.defaultIcon_ = icon;
};

SimpleMap.prototype.setCenter = function(latLng) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  this.map.setCenter(latLng, this.defaultZoom_);
};

SimpleMap.prototype.setCenterGeocode = function(locationString) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  var me = this;
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.setCenter(latLng);
    }
  });
};

SimpleMap.prototype.addMarker = function(lat, lng, opt_suffix) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  var latLng = new GLatLng(lat, lng);
  var url = 'http://www.google.com/mapfiles/marker_midblue' +
      [opt_suffix === undefined ? '' : opt_suffix] +
      '.png';
  this.map.addOverlay(new GMarker(latLng, new GIcon(this.defaultIcon_, url)));
};

SimpleMap.prototype.addMarkerGeocode = function(locationString) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  var me = this;
  // TODO(paul): Use .getLocations() method instead, to get accuracy rating.
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.addMarker(latLng.lat(), latLng.lng());
    }
  });
};

/** callback is a function that accepts a GLatLng and an accuracy.
 */
SimpleMap.prototype.geocode = function(locationString, callback) {
  if (!GBrowserIsCompatible()) {
    return;
  }
  var me = this;
  this.geocoder_.getLatLng(locationString, function(latLng) {
    // TODO: implement accuracy.
    callback(latLng, 0);
  });
};
