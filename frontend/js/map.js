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
function SimpleMap(div) {
  this.div_ = div;
  this.defaultZoom_ = 10;

  if (GBrowserIsCompatible()) {
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

    if (false) {
      this.icon_ = new GIcon(G_DEFAULT_ICON, "/images/markers/red.png");
      this.icon_.iconSize.width = 32;
      this.icon_.iconSize.height = 32;
      this.icon_.iconAnchor.x = 15;
      this.icon_.iconAnchor.y = 31;
    }
    return this;
  } else {
    return null;
  }
}

SimpleMap.prototype.setCenter = function(latLng) {
  this.map.setCenter(latLng, this.defaultZoom_);
}

SimpleMap.prototype.setCenterGeocode = function(locationString) {
  var me = this;
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.setCenter(latLng);
    }
  });
}

SimpleMap.prototype.addMarker = function(lat, lng) {
  var latLng = new GLatLng(lat, lng);
  this.map.addOverlay(new GMarker(latLng, this.icon_));
}

SimpleMap.prototype.addMarkerGeocode = function(locationString) {
  var me = this;
  // TODO(paul): Use .getLocations() method instead, to get accuracy rating.
  this.geocoder_.getLatLng(locationString, function(latLng) {
    if (latLng) {
      me.addMarker(latLng.lat(), latLng.lng());
    }
  });
}

/** callback is a function that accepts a GLatLng and an accuracy.
 */
SimpleMap.prototype.geocode = function(locationString, callback) {
  var me = this;
  this.geocoder_.getLatLng(locationString, function(latLng) {
    // TODO: implement accuracy.
    callback(latLng, 0);
  });
}
