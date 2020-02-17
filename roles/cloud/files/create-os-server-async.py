#!/usr/bin/env python

# A wrapper around the OpenStack SDK to create
# OpenStack server instances (asynchronously).
#
# Note:     This module DOES NOT provide all the functionality of
# ----      the underlying API, just those bits I need for my work.
#
# You will need your OpenStack environment variables defined
# and the Python openstacksdk module...
#
#   $ pip install openstacksdk
#   $ ./create-os-server-async.py --help
#
# Typical call to create 64 server instances
# called "graph-worker-1" to "graph-worker-64": -
#
#   $ ./create-os-server.py \
#           --name graph-worker \
#           --image ScientificLinux-7-NoGui \
#           --flavour c3.large \
#           --keypair graph-key \
#           --count 64 \
#           --verbose
#
# Refer to the connection API in the openstacksdk for background:
# https://docs.openstack.org/openstacksdk/latest/user/connection.html

import argparse
import sys
import time

import openstack


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
           keypair_name,
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
    :param keypair_name: The OpenStack SSH key-pair to use (this must exist)
    :param verbose: Generate helpful progress.
    :returns: False on failure
    """
    image = conn.compute.find_image(image_name)
    if not image:
        print('Unknown image ({})'.format(image_name))
        return ServerResult(False, False, 0)
    flavour = conn.compute.find_flavor(flavour_name)
    if not flavour:
        print('Unknown flavour ({})'.format(flavour_name))
        return ServerResult(False, False, 0)
    # Optional network supplied?
    network_info = []
    if network_name:
        network = conn.network.find_network(network_name)
        if not network:
            print('Unknown network ({})'.format(network_name))
            return False
        network_info.append({'uuid': network.id})

    # Do nothing if the server appears to exist
    if conn.get_server(name_or_id=server_name):
        # Yes!
        # Success, unchanged
        if verbose:
            print('Server ({}) already exists'.format(server_name))
        return False

    # The number of times we had to re-create this server instance.
    num_create_failures = 0

    create_begin_time = time.time()
    if verbose:
        print('Creating server ({})...'.format(server_name))

    try:
        conn.compute.create_server(name=server_name,
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
        return False

    create_end_time = time.time()
    if verbose:
        create_duration = create_end_time - create_begin_time
        print('Create duration: {0:.2f}S'.format(create_duration))

    # Set 'changed'.
    # If not successful this is ignored.
    return True


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

# Defaults...
PARSER.add_argument('-c', '--count',
                    help='The count of the number of instances to create.'
                         ' If more than one "-<n>" is appended to the name '
                         ' given name, where <n> has the value "1" to "count"',
                    type=positive_int_non_zero,
                    default=1)
PARSER.add_argument('-v', '--verbose',
                    help='Generate helpful output.',
                    action='store_true')

ARGS = PARSER.parse_args()

# Create an OpenStack connection.
# No arguments - this relies on suitable variables
# being set in the user's environment.
connection = openstack.connect()

# Crete the server instances until we have an error
# we can't handle...

for i in range(0, ARGS.count):
    n_id = i + 1
    name = ARGS.name if ARGS.count == 1 else '{}-{}'.format(ARGS.name, n_id)
    server_result = create(connection, name,
                           ARGS.image, ARGS.flavour, ARGS.network,
                           ARGS.keypair,
                           ARGS.verbose)
    if not server_result:
        # Something went wrong.
        # Leave.
        sys.exit(1)

# Success if we get here...
