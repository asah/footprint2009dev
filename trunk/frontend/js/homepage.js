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
var searches = [ 'Clean up', 'Education', 'Hunger', 'Tutor',
    'Homeless', 'Seniors', 'Health', 'Animals', 'Hospital', 'Developer' ];
for (var i = 0; i < searches.length; i++) {
  var html = '<a href="/search?q=' + searches[i] + '">' +
      searches[i] + '<' + '\a>';
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
  var newLocation = el('location').value;
  window.location.href = '/search#vol_loc=' + escape(el('location').value);
}
