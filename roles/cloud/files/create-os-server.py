#!/usr/bin/env python

# A create-server utility as it would have been written by 'Robert I'.
# A wrapper around the OpenStack SDK to try (and try again) to create
# OpenStack server instances.
#
# Note:     This module DOES NOT provide all the functionality of
# ----      the underlying API, just those bits I need for my work.
#
# You will need your OpenStack environment variables defined
# and the Python openstacksdk module...
#
#   $ pip install openstacksdk
#   $ ./create-os-server.py --help
#
# Typical call to create 64 server instances
# called "graph-worker-1" to "graph-worker-64": -
#
#   $ ./create-os-server.py \
#           --name graph-worker \
#           --image ScientificLinux-7-NoGui \
#           --flavour c3.large \
#           --keypair graph-key \
#           --count 64
#
# Or, to create one instance
# whose name is exactly as provided: -
#
#   $ ./create-os-server.py \
#           --name graph-worker \
#           --image ScientificLinux-7-NoGui \
#           --flavour c3.large \
#           --keypair graph-key
#
# Refer to the connection API in the openstacksdk for background:
# https://docs.openstack.org/openstacksdk/latest/user/connection.html

import argparse
import sys
import time
from collections import namedtuple

import openstack

# ServerResult.
# success   is True on success.
# changed   If successful, changed is True if the server was created,
#           and False if it already existed.
# failures  The number of server creation failures creating the server
ServerResult = namedtuple('ServerResult', 'success changed failures')

MAX_DELAY = 120


def positive_int_non_zero(value):
    """Used as an argparse type validator.
    Checks the value is a suitable integer.

    :param value:  string representation of an integer
    """
    try:
        int_value = int(value)
    except ValueError:
        raise argparse. \
            ArgumentTypeError("%s is not an integer" % value)
    if int_value <= 0:
        raise argparse.\
            ArgumentTypeError("%s is an invalid positive int value" % value)
    return int_value


def create(conn,
           server_name,
           image_name,
           flavour_name,
           network_name,
           ips,
           keypair_name,
           attempts,
           retry_delay_s,
           wait_time_s,
           verbose=False):
    """Create an OpenStack server. Automatically deletes and retries
    the creation process until a server is available. Once the creation
    attempts have been exhausted the function returns False.

    The server creation can fail, that's fatal for us. If the
    'wait' fails then we created a server and it failed for some reason.
    We delete the server and try again under these circumstances.

    :param conn: The OpenStack connection
    :param server_name: The server name
    :param image_name: The server instance base image
    :param flavour_name: The server flavour (type), i.e. 'c2.large'
    :param network_name: The (optional) network name, or None
    :param ips: A (possibly empty) list of IPs to assign to the server
    :param keypair_name: The OpenStack SSH key-pair to use (this must exist)
    :param attempts: The number of create attempts. If the server fails
                     this function uses this value to decide whether to try
                     ans create it.
    :param retry_delay_s: The delay between creation attempts.
    :param wait_time_s: The maximum period to wait (for creation or deletion).
    :param verbose: Generate helpful progress.
    :returns: False on failure
    """
    image = conn.compute.find_image(image_name)
    if not image:
        print('Unknown image ({})'.format(image_name))
        return ServerResult(False, False)
    flavour = conn.compute.find_flavor(flavour_name)
    if not flavour:
        print('Unknown flavour ({})'.format(flavour_name))
        return ServerResult(False, False)
    # Optional network supplied?
    network_info = []
    if network_name:
        network = conn.network.find_network(network_name)
        if not network:
            print('Unknown network ({})'.format(network_name))
            return ServerResult(False, False)
        network_info.append({'uuid': network.id})

    # Do nothing if the server appears to exist
    if conn.get_server(name_or_id=server_name):
        # Yes!
        # Success, unchanged
        return ServerResult(True, False)

    # The number of times we had to re-create this server instance.
    num_create_failures = 0

    attempt = 1
    success = False
    while not success and attempt <= attempts:

        if verbose:
            print('Creating {}...'.format(server_name))
        try:
            server = conn.compute.create_server(name=server_name,
                                                image_id=image.id,
                                                flavor_id=flavour.id,
                                                key_name=keypair_name,
                                                networks=network_info,
                                                wait=True)
        except openstack.exceptions.HttpException as ex:
            # Something wrong creating the server.
            # Nothing we can do here.
            print('ERROR: HttpException ({})'.format(server_name))
            print(ex)
            return ServerResult(False, False)

        new_server = None
        try:
            new_server = conn.compute.wait_for_server(server,
                                                      wait=wait_time_s)
            if ips:
                conn.add_ip_list(new_server, ips)
        except openstack.exceptions.ResourceFailure:
            print('ERROR: ResourceFailure ({})'.format(server_name))
        except openstack.exceptions.ResourceTimeout:
            print('ERROR: ResourceTimeout/create ({})'.format(server_name))

        if new_server:
            success = True
        else:
            # Failed to create a server.
            # Count it.
            num_create_failures += 1
            if verbose:
                print('Failed ({}) attempt no {}.'.format(server_name, attempt))
            # Delete the instance
            # (unless this is our last attempt)
            if attempt < attempts:
                if verbose:
                    print('Deleting... ({})'.format(server_name))
                # Delete the instance
                # and wait for it...
                conn.compute.delete_server(server)
                try:
                    conn.compute.wait_for_delete(server,
                                                 wait=wait_time_s)
                except openstack.exceptions.ResourceTimeout:
                    print('ERROR: ResourceTimeout/delete ({})'.format(server_name))
                if verbose:
                    print('Pausing...')
                time.sleep(retry_delay_s)
            attempt += 1

    # Set 'changed'.
    # If not successful this is ignored.
    return ServerResult(success, True, num_create_failures)


# Configure the command-line parser
# ans process the command-line...
PARSER = argparse.ArgumentParser(description='Create OpenStack Servers')

# Mandatory...
PARSER.add_argument('-n', '--name',
                    help='The server name, a base-name if the count '
                         ' is greater than "1"',
                    required=True)
PARSER.add_argument('-f', '--flavour',
                    help='The server flavour (type), i.e. c3.large',
                    required=True)
PARSER.add_argument('-i', '--image',
                    help='The image name to base the server on',
                    required=True)
PARSER.add_argument('-p', '--keypair',
                    help='The OpenStack keypair,'
                         ' which must exist in your OpenStack account',
                    required=True)

# Optional...
PARSER.add_argument('-k', '--network',
                    help='The network name to use')
PARSER.add_argument('-s', '--ips',
                    nargs='+',
                    default=[],
                    help='IPs to assign to the server.'
                         ' Only valid if --count is unused or "1"')

# Defaults...
PARSER.add_argument('-a', '--attempts',
                    help='Number of attempts at creating a server (1 or more)',
                    type=int,
                    default=6)
PARSER.add_argument('-d', '--retry-delay',
                    help='The delay (in seconds) between retry attempts'
                         ' when the server fails to be created (1..120)',
                    type=positive_int_non_zero,
                    default=10)
PARSER.add_argument('-c', '--count',
                    help='The count of the number of instances to create.'
                         ' If more than one "-<n>" is appended to the name '
                         ' given name, where <n> has the value "1" to "count"',
                    type=positive_int_non_zero,
                    default=1)
PARSER.add_argument('-w', '--wait-time',
                    help='The maximum period (seconds) to wait for a server'
                         ' to get created (or destroyed).',
                    type=positive_int_non_zero,
                    default=120)
PARSER.add_argument('-v', '--verbose',
                    help='Generate helpful output.',
                    action='store_true')

ARGS = PARSER.parse_args()

# Extra validation for the given arguments...
if ARGS.retry_delay > MAX_DELAY:
    print('--retry-delay (%s) is too large' % ARGS.retry_delay)
    sys.exit(1)
if ARGS.ips and ARGS.count > 1:
    print('Can only use --ips if --count is 1')
    sys.exit(1)

# Create an OpenStack connection.
# No arguments - this relies on suitable variables
# being set in the user's environment.
connection = openstack.connect()

# Crete the server instances until we have an error
# we can't handle...

# Number of servers that needed at least 1 attempt
num_servers_that_had_trouble = 0
num_server_consecutive_failures = 0
num_server_create_failures = 0
failed_workers = []
for i in range(0, ARGS.count):
    n_id = i + 1
    name = ARGS.name if ARGS.count == 1 else '{}-{}'.format(ARGS.name, n_id)
    server_result = create(connection, name,
                           ARGS.image, ARGS.flavour, ARGS.network, ARGS.ips,
                           ARGS.keypair,
                           ARGS.attempts, ARGS.retry_delay, ARGS.wait_time,
                           ARGS.verbose)
    if not server_result.success:
        # Something went wrong.
        # Leave.
        sys.exit(1)
    elif server_result.failures:
        num_servers_that_had_trouble += 1
        num_server_create_failures += server_result.failures
        failed_workers.append(n_id)
        if server_result.failures > num_server_consecutive_failures:
            num_server_consecutive_failures = server_result.failures

# Success if we get here...
#
# Print a summary of the failures
print('Cloud server create failures: {}'.format(num_server_create_failures))
print('Cloud server max consecutive failures: {}'.format(num_server_consecutive_failures))
print('Cloud servers needing help: {}'.format(num_servers_that_had_trouble))
print('Cloud servers failed: {}'.format(failed_workers))
# We (Ansible) expects 'Cloud changed: True'
# to use for its changed_when variable.
print('Cloud changed: {}'.format(server_result.changed))
