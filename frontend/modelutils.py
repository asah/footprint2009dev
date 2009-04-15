#!/usr/bin/python2.5
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

"""Datastore helper methods."""

import datetime
import logging

from google.appengine.api import memcache
from google.appengine.ext import db


def IncrementProperties(model_class, key, props_to_set, **kwargs):
  """Generic method to increment statistics. Can also set properties.

  Example:

  Args:
    model_class: model class
    key: Entity key.
    props_to_set: Dictionary of properties to set to explicit values.
    kwargs: Properties to increment by specified amount.
  """

  def txn():
    stats = model_class.get_by_key_name(key)
    if not stats:
      stats = model_class(key_name=key)

    def increment(prop):
      if getattr(stats, prop):
        setattr(stats, prop, getattr(stats, prop) + kwargs[prop])
      else:
        setattr(stats, prop, kwargs[prop])

    # Set explicit values first.
    if props_to_set:
      for prop in props_to_set.iterkeys():
        setattr(stats, prop, props_to_set[prop])

    # Increment properties by requested amount.
    for prop in kwargs.iterkeys():
      increment(prop)

    stats.put()
    return stats

  return db.run_in_transaction(txn)


def get_by_ids(cls, ids, memcache_prefix=None, datastore_prefix=None):
  """Gets multiple entities for IDs, trying memcache then datastore.

  Args:
    cls: Model class
    ids: list of ids.
    memcache_prefix: The prefix (of id) used to store the model in memcache.
        Defaults to cls.MEMCACHE_PREFIX.
    datastore_prefix: The prefix used to store the model in datastore.
        Defaults to cls.DATASTORE_PREFIX.
  Returns:
    Dictionary of results, id:model.
  """
  results = {}
  try:
    results = memcache.get(ids, memcache_prefix + ':')
  except Exception:
    pass  # Memcache is busted. Oh well.

  if not memcache_prefix:
    memcache_prefix = cls.MEMCACHE_PREFIX
  if not datastore_prefix:
    datastore_prefix = cls.DATASTORE_PREFIX

  missing_ids = []
  for id in ids:
    if not id in results:
      missing_ids.append(datastore_prefix + id)

  datastore_results = cls.get_by_key_name(missing_ids)
  for result in datastore_results:
    if result:
      result_id = result.key().name()[len(datastore_prefix):]
      results[result_id] = result

  return results
