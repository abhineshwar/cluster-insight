#!/usr/bin/python
#
# Copyright 2015 The Cluster-Insight Authors. All Rights Reserved
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

"""Annotates nodes and containers with Heapster metric query parameters.

TODO(eran):
The current code uses fixed lookup tables for metric names and label
names. It should be replaced with code that fetch the metric names from
Heapster. It is dependent on issue
https://github.com/GoogleCloudPlatform/heapster/issues/241.
"""

# global imports
import copy
import types

# local imports
import utilities

METRIC_PREFIX = 'custom.cloudmonitoring.googleapis.com/kubernetes.io/'
METRIC_NAMES = [
    METRIC_PREFIX + 'cpu/usage',
    METRIC_PREFIX + 'memory/page_faults',
    METRIC_PREFIX + 'memory/usage',
    METRIC_PREFIX + 'memory/working_set',
    METRIC_PREFIX + 'network/rx',
    METRIC_PREFIX + 'network/rx_errors',
    METRIC_PREFIX + 'network/tx',
    METRIC_PREFIX + 'network/tx_errors',
    METRIC_PREFIX + 'uptime'
]


def _get_container_labels(container, parent_pod):
  """Returns key/value pairs identifying all metrics of this container.

  Args:
    container: the container object to annotate.
    parent_pod: the parent pod of 'container'.

  Returns:
  A dictionary of key/value pairs.
  If any error was detected, returns None.
  """
  if not utilities.is_wrapped_object(container, 'Container'):
    return None
  if not utilities.is_wrapped_object(parent_pod, 'Pod'):
    return None

  pod_id = utilities.get_attribute(
      parent_pod, ['properties', 'metadata', 'uid'])
  if not utilities.valid_string(pod_id):
    return None

  hostname = utilities.get_attribute(
      parent_pod, ['properties', 'spec', 'host'])
  if not utilities.valid_string(hostname):
    return None

  short_container_name = utilities.get_short_container_name(
      container, parent_pod)

  if not utilities.valid_string(short_container_name):
    return None

  return {
      'pod_id': pod_id,
      'hostname': hostname,
      'container_name': short_container_name
  }


def _get_node_labels(node):
  """Returns key/value pairs identifying all metrics of this node.

  Args:
    node: the node object to annotate.

  Returns:
  A dictionary of key/value pairs.
  If any error was detected, returns None.
  """
  if not utilities.is_wrapped_object(node, 'Node'):
    return None

  hostname = utilities.get_attribute(node, ['properties', 'metadata', 'name'])
  if not utilities.valid_string(hostname):
    return None

  return {
      'pod_id': '',
      'hostname': hostname,
      'container_name': '/'
  }


def _make_gcm_metrics(project_id, labels_dict):
  """Generate a descriptor of GCM metrics from 'project_id' and 'labels_dict'.

  Args:
    project_id: the project ID
    labels_dict: the key/value pairs that identify all metrics of the
    current resource.

  Returns:
  A dictionary containing the descriptor of the GCM metrics.
  See below for details.
  If 'labels_dict' is None, returns None.

  Typical output is:
  {
    'gcm': {
      'names': ['.../cpu/usage', '.../memory/page_faults', ...],
      'project': PROJECT,
      'labels_prefix': PREFIX,
      'labels': {
         'pod_id': POD_ID, 'hostname': HOSTNAME,
         'container_name': CONTAINER_NAME }
    }
  }
  """
  if labels_dict is None:
    return None

  assert utilities.valid_string(project_id)
  assert isinstance(labels_dict, types.DictType)

  if not labels_dict:
    # an empty dictionary
    return None

  return {'gcm': {
      'names': copy.deepcopy(METRIC_NAMES),
      'project': project_id,
      'labels': copy.deepcopy(labels_dict),
      'labels_prefix': METRIC_PREFIX + 'label/'
  }}


def annotate_container(project_id, container, parent_pod):
  """Annotate the given container with Heapster GCM metric information.

  Args:
    project_id: the project ID
    container: the container object to annotate.
    parent_pod: the parent pod of 'container'.

  Raises:
    AssertionError: if the input arguments are invalid or if
    'parent_pod' is not the parent of 'container'
  """
  assert utilities.valid_string(project_id)
  assert utilities.is_wrapped_object(container, 'Container')
  assert utilities.is_wrapped_object(parent_pod, 'Pod')
  parent_name = utilities.get_attribute(
      container, ['properties', 'Config', 'Hostname'])
  assert utilities.valid_string(parent_name)
  pod_name = utilities.get_attribute(
      parent_pod, ['properties', 'metadata', 'name'])
  assert utilities.valid_string(pod_name)

  # The 'parent_name' value is truncated to the first 64 characters.
  # Thus it must be the prefix of the full pod name.
  assert pod_name.startswith(parent_name)

  m = _make_gcm_metrics(
      project_id, _get_container_labels(container, parent_pod))
  if m is None:
    return
  if container.get('annotations') is None:
    container['annotations'] = {}
  container['annotations']['metrics'] = m


def annotate_node(project_id, node):
  """Annotate the given node with Heapster GCM metric information.

  Args:
    project_id: the project ID
    node: the node object to annotate.

  Raises:
    AssertionError: if the input argument is invalid.
  """
  assert utilities.valid_string(project_id)
  assert utilities.is_wrapped_object(node, 'Node')

  m = _make_gcm_metrics(project_id, _get_node_labels(node))
  if m is None:
    return
  if node.get('annotations') is None:
    node['annotations'] = {}
  node['annotations']['metrics'] = m
