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

if (getDefaultLocation().displayLong) {
  el('mini_with_location').style.display = '';
} else {
  el('mini_without_location').style.display = '';
  el('location_form').style.display = '';
}

var defaultLocation = getDefaultLocation().displayLong || '';
setInputFieldValue(el('location'), defaultLocation);

el('more_link').href = 'javascript:submitForm("");void(0);';

function goPopular(index) {
  setInputFieldValue(el('keywords'), popularSearches[index]);
  submitForm('');
}

// Populate the popular searches list.
for (var i = 0; i < popularSearches.length; i++) {
  var href = 'javascript:goPopular(' + i + ');void(0);';
  var html = '<a href="' + href + '">' +
      popularSearches[i] + '<' + '\a>';
  el('popular_list').innerHTML += html + '<br>';
}

var vol_loc_term;
if (defaultLocation != '') {
  vol_loc_term = '&vol_loc=' + defaultLocation;
} else {
  // TODO: Make these the defaults inside search.py/base_search.py.
  //       Will then need to test that "No Results" message doesn't
  //       show "USA".
  vol_loc_term = '&vol_loc=USA&vol_dist=1500';
}
var url = '/ui_snippets?start=0&num=4&minimal_snippets_list=1' + vol_loc_term;


setTextContent(el('location_text'), defaultLocation);

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