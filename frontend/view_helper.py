# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utilities that support views.py.
"""

import base_search
import logging
import models
import modelutils

def get_user_interests(user, remove_no_interest):
  """Get the opportunities a user has expressed interest in.

  Args:
    user: userinfo.User of a user
    remove_no_interest: Filter out items with no expressed interest.
  Returns:
    Dictionary of volunteer opportunity id: expressed interest (liked).
  """
  user_interests = {}
  if user:
    # Note that if a user has a lot (particularly > 1000) of
    # UserInterest entries, we'll have to do a more clever
    # query than the magic reverse reference query.
    for interest in user.get_user_info().interests:
      interest_value = getattr(interest, models.USER_INTEREST_LIKED)
      if not remove_no_interest or interest_value != 0:
        user_interests[interest.opp_id] = interest_value
    #logging.info('Found interests: %s' % user_interests)
  return user_interests


def get_interest_for_opportunities(opp_ids):
  """Get the interest statistics for a set of volunteer opportunities.

  Args:
    opp_ids: list of volunteer opportunity ids.

  Returns:
    Dictionary of volunteer opportunity id: aggregated interest values.
  """
  others_interests = {}

  interests = modelutils.get_by_ids(models.VolunteerOpportunityStats, opp_ids)
  for (item_id, interest) in interests.iteritems():
    if interest:
      others_interests[item_id] = getattr(interest, models.USER_INTEREST_LIKED)
  return others_interests


def get_annotated_results(user, result_set):
  """Get results annotated with the interests of this user and all users.

  Args:
    user: User object returned by userinfo.get_user()
    result_set: A search.SearchResultSet.
  Returns:
    The incoming result set, annotated with user-specific info.
  """

  # Get all the ids of items we've found
  opp_ids = [result.item_id for result in result_set.results]

  # mark the items the user is interested in
  user_interests = get_user_interests(user, True)

  # note the interest of others
  others_interests = get_interest_for_opportunities(opp_ids)

  return annotate_results(user_interests, others_interests, result_set)


def annotate_results(user_interests, others_interests, result_set):
  """Annotates results with the provided interests.

  Args:
    user_interests: User interests from get_user_interests. Can be None.
    others_interests: Others interests from get_interest_for_opportunities.
                      Can be None.
    result_set: A search.SearchResultSet.
  Returns:
    The incoming result set, annotated with user-specific info.
  """

  # Mark up the results
  for result in result_set.results:
    if user_interests and result.item_id in user_interests:
      result.interest = user_interests[result.item_id]
    if others_interests and result.item_id in others_interests:
      #logging.info("others interest in %s = %s " % \
      #  (result.item_id, others_interests[result.item_id]))
      # TODO: Consider updating the base url here if it's changed.
      result.interest_count = others_interests[result.item_id]

  return result_set


def get_my_snippets_view_data(user_info):
  """Preps the data required to render the "My Events" aka "Profile" template.
  Args:
    user_info: userinfo.User for the current user.
  Returns:
    Dictionary of data required to render the template.
  """

  # Get the list of all events that I like or am doing.
  my_event_ids_and_interests = get_user_interests(user_info, True)
  my_events_result_set = base_search.get_from_ids(my_event_ids_and_interests)
  # TODO: Handle the difference between liking and doing.
  # TODO: Reconcile with annotate functions above.
  for result in my_events_result_set.results:
    result.interest = my_event_ids_and_interests[result.item_id]
    
  # TODO: Handle pagination.
  my_events_result_set.clipped_results = my_events_result_set.results

  # Get general interest numbers (i.e., not filtered to friends).
  event_ids_and_interest_stats = \
    get_interest_for_opportunities(my_event_ids_and_interests)
  annotate_results(my_event_ids_and_interests, event_ids_and_interest_stats,
                   my_events_result_set)
  # Get the list of all my friends.
  # Assemble the opportunities your friends have starred.
  friends = user_info.load_friends()
  
  # For each of my friends, get the list of all events that that friend likes
  # or is doing.
  # For each of the events found, cross-reference the list of its interested
  # users.
  friend_opp_count = {}
  friends_by_event_id_js = {}
  for friend in friends:
    friend_event_ids = get_user_interests(friend, True)
    for event_id in friend_event_ids:
      count = friend_opp_count.get(event_id, 0)
      friend_opp_count[event_id] = count + 1
      uids = friends_by_event_id_js.get(event_id, [])
      uids.append(friend.user_id)
      friends_by_event_id_js[event_id] = uids

  # Leverage the similarity of js and python object & array formats
  # to produce a serialized form that can be used client-side.
  # TODO(timman): Use the simplejson library.
  friends_by_event_id_js = \
      repr(friends_by_event_id_js).replace('u\'', '\'')

  view_vals = {
    'has_results': len(my_events_result_set.results) > 0,
    'friends': friends,
    'result_set': my_events_result_set,
    'friends_by_event_id_js': friends_by_event_id_js,
  }

  return view_vals
