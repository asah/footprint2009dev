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
TODO: module docs go here?!
"""

import logging
import re

#from google.appengine.api import users

import base_search
import models
#import search
import userinfo

def get_user_interests(user, remove_no_interest):
  """Get the opportunities a user has expressed interest in.

  Args:
    user: userinfo.User of a user
    remove_no_interest: Filter out items with expressed_interest = UNKNOWN.
  Returns:
    Dictionary of volunteer opportunity id: expressed_interest.
  """
  user_interests = {}
  if user:
    # Note that if a user has a lot (particularly > 1000) of
    # UserInterest entries, we'll have to do a more clever
    # query than the magic reverse reference query.
    for interest in user.get_user_info().interests:
      if (not remove_no_interest or
          interest.expressed_interest != models.InterestTypeProperty.UNKNOWN):
        # TODO: Eliminate "3:" as a hardcoded range -- bug-prone.
        user_interests[interest.key().name()[3:]] = interest.expressed_interest
    #logging.info('Found interests: %s' % user_interests)
  return user_interests

def get_interest_for_opportunities(opp_ids):
  """Get the interest statistics for a set of volunteer opportunities.

  Args:
    opp_ids: list of volunteer opportunity ids.

  Returns:
    Dictionary of volunteer opportunity id: interested_count.
  """
  others_interests = {}

  interests = models.get_by_ids(models.VolunteerOpportunityStats, opp_ids)
  for (id, interest) in interests.iteritems():
    if interest:
      others_interests[id] = interest.interested_count
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
  opp_ids = [result.id for result in result_set.results];

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
    if user_interests and result.id in user_interests:
      result.interest = user_interests[result.id]
    if others_interests and result.id in others_interests:
      #logging.info("others interest in %s = %s " % (result.id, others_interests[result.id]))
      # TODO: Consider updating the base url here if it's changed.
      result.interest_count = others_interests[result.id]

  return result_set


def get_data_for_friends_view(user_info, is_debug):
  """Preps the data required to render the "Work with others" template.

  Args:
    user_info: userinfo.User for the current user.
    is_debug: If passed, prepares the data for debug/test mode.
  Returns:
    Dictionary of data required to render the template.
  """

  # Load details for the opportunities that the current user has starred.
  current_user_opps_ids = get_user_interests(user_info, True)
  current_user_opps_result_set = base_search.get_from_ids(current_user_opps_ids)
  
  # Annotate each opportunity with its overall stars count (i.e., not
  # filtered by the current user's friends.
  others_interests = get_interest_for_opportunities(current_user_opps_ids)
  for result in current_user_opps_result_set.results:
    if result.id in others_interests:
      result.overall_interest_count = others_interests[result.id]

  # Assemble the opportunities your friends have starred.        
  friends = user_info.load_friends()
  friend_opp_count = {}
  friend_interests_by_oid = {}
  friend_total_opp_count = 0
  for friend in friends:
    friend_opp_ids = get_user_interests(friend, True)
    if is_debug:
      #Temp dev workaround for starring bug, just pretend your friends
      #like all the same things you do.
      #TODO: http://code.google.com/p/footprint2009dev/issues/detail?id=40
      friend_opp_ids = current_user_opps_ids

    friend.interest_count = len(friend_opp_ids)
    
    # Assemble the per-opportunity friend-star count and total friend-star count
    for opp_id in friend_opp_ids:
      count = friend_opp_count.get(opp_id, 0)
      friend_opp_count[opp_id] = count + 1
      friend_total_opp_count += 1
      uids = friend_interests_by_oid.get(opp_id, [])
      uids.append(friend.user_id)
      friend_interests_by_oid[opp_id] = uids

  # Leverage the similarity of js and python object & array formats
  # to produce a serialized form that can be used client-side.
  # TODO(timman): Use a real json library.
  friend_interests_by_oid_js = repr(friend_interests_by_oid).replace('u\'', '\'')

  # Annotate each opportunity with its friends-specific stars count.
  for result in current_user_opps_result_set.results:
    if result.id in friend_opp_count:
      result.friends_interest_count = friend_opp_count[result.id]

  view_vals = {
    'has_results': len(current_user_opps_result_set.results) > 0,
    'friends': friends,
    'current_user_opps_result_set': current_user_opps_result_set,
    'current_user_opps_ids': current_user_opps_ids,
    'friend_total_opp_count': friend_total_opp_count,
    'friend_interests_by_oid_js': friend_interests_by_oid_js,
  }
  
  return view_vals
