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

// TODO(paul): Verify ClientLocation.address/coords are defined

var coords = getClientLocation().coords || '';
var city = getClientLocation().city || '';

var vol_loc_term = '';
if (coords) {
  vol_loc_term = 'vol_loc=' + coords + '&';
  el('mini_with_location').style.display = '';
} else {
  el('mini_without_location').style.display = '';
  el('location_form').style.display = '';
}

el('more_link').href = '/search?' + vol_loc_term;

// Populate the popular searches list.
for (var i = 0; i < popularSearches.length; i++) {
  var html = '<a href="/search?q=' + popularSearches[i] + '">' +
      popularSearches[i] + '<' + '\a>';
  el('popular_list').innerHTML += html + '<br>';
}

var url = '/ui_snippets?start=0&num=6&minimal_snippets_list=1&' + vol_loc_term;

el('location_text').innerHTML = city;
jQuery.ajax({
      url: url,
      async: true,
      dataType: 'html',
      error: function(){},
      success: function(data){
        if (data.length > 10) {  // Check if data is near-empty.
          el('snippets').innerHTML = data;
          el('more').style.display = '';
        }
      }
    });

setInputFieldValue(el('location'), '');

function changeLocation() {
  var newLocation = getInputFieldValue(el('location'));
  window.location.href = '/search#vol_loc=' + escape(newLocation);
}
