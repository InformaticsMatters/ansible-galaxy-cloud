#!/usr/bin/env python

# A create-server utility as it would have been written by 'Robert I'.
# A wrapper around the OpenStack SDK to try (and try again) to create
# OpenStack server instances.
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
# Or, to create one instance: -
#
#   $ ./create-os-server.py \
#           --name graph-worker \
#           --image ScientificLinux-7-NoGui \
#           --flavour c3.large \
#           --keypair graph-key \
#           --count 64

import argparse
import sys
import time

import openstack

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
           floating_ips,
           keypair_name,
           attempts,
           retry_delay_s,
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
    :param floating_ips: A (possibly empty) list of floating IPs
    :param keypair_name: The OpenStack SSH key-pair to use (this must exist)
    :param attempts: The number of create attempts. If the server fails
                     this function uses this value to decide whether to try
                     ans create it.
    :param retry_delay_s: The delay between creation attempts.
    :param verbose: Generate helpful progress.
    :returns: False on failure
    """
    image = conn.compute.find_image(image_name)
    if not image:
        print('Unknown image ({})'.format(image_name))
        return False
    flavour = conn.compute.find_flavor(flavour_name)
    if not flavour:
        print('Unknown flavour ({})'.format(flavour_name))
        return False
    # Optional network supplied?
    network_info = []
    if network_name:
        network = conn.network.find_network(network_name)
        if not network:
            print('Unknown network ({})'.format(network_name))
            return False
        network_info.append({'uuid': network.id})

    attempt = 1
    success = False
    while not success and attempt <= attempts:

        if verbose:
            print('Creating {}...'.format(server_name))
        try:
            server = conn.compute.create_server(name=server_name,
                                                image_id=image.id,
                                                flavor_id=flavour.id,
                                                floating_ips=floating_ips,
                                                key_name=keypair_name,
                                                networks=network_info)
        except openstack.exceptions.HttpException as ex:
            # Something wrong creating the server.
            # Nothing we can do here.
            print('ERROR: HttpException ({})'.format(server_name))
            print(ex)
            return False

        new_server = None
        try:
            new_server = conn.compute.wait_for_server(server)
        except openstack.exceptions.ResourceFailure:
            print('ERROR: ResourceFailure ({})'.format(server_name))
        except openstack.exceptions.ResourceTimeout:
            print('ERROR: ResourceTimeout ({})'.format(server_name))

        if new_server:
            success = True
        else:
            if verbose:
                print('Failed ({}) attempt no {}.'.format(server_name, attempt))
            # Delete the instance
            # (unless this is our last attempt)
            if attempt < attempts:
                if verbose:
                    print('Deleting... ({})'.format(server_name))
                conn.compute.delete_server(server)
                if verbose:
                    print('Pausing...')
                time.sleep(retry_delay_s)
            attempt += 1

    return success


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
PARSER.add_argument('-l', '--floating-ips',
                    default=[],
                    nargs='+',
                    help='Floating IPs to assign to the server.'
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
PARSER.add_argument('-v', '--verbose',
                    help='Generate helpful output.',
                    action='store_true')

ARGS = PARSER.parse_args()
print(ARGS)

# Extra validation for the given arguments...
if ARGS.retry_delay > MAX_DELAY:
    print('retry-delay (%s) is too large' % ARGS.retry_delay)
    sys.exit(1)
if ARGS.floating_ips and ARGS.count > 1:
    print('Can only use floating-ips if count is 1')
    sys.exit(1)

# Create an OpenStack connection.
# No arguments - this relies on suitable variables
# being set in the user's environment.
connection = openstack.connect()

# Crete the server instances until we have an error
# we can't handle...
for i in range(1, ARGS.count):
    name = ARGS.name if ARGS.count == 1 else '{}-{}'.format(ARGS.name, i)
    if not create(connection, name,
                  ARGS.image, ARGS.flavour, ARGS.network, ARGS.floating_ips,
                  ARGS.keypair,
                  ARGS.attempts, ARGS.retry_delay,
                  ARGS.verbose):
        # Something went wrong.
        # Leave.
        sys.exit(1)

# Success if we get here...
