#!/usr/bin/env bash

# A template for 'graph-cloud' playbook environment variables.
# These variables contain potentially sensitive information and
# are therefore not captured within the Ansible playbooks.
#
# The playbooks assert that salient variables are set so it should
# be obvious if something's missing.
#
# Prior to running the playbooks...
#
# - Copy this file as 'site-setenv.sh'
#   (protected from accidental commits by the project .gitignore)
# - Populate your 'site-setenv.sh' file with real values
# - Run 'source site-setenv.sh'
#
# Additionally ... You will need to provide environment variables
#                  for your chosen cloud provider (currently just OpenStack).
#                  For example, for OpenStack you need to source/use the
#                  'keystone' file you've been given.

export PULSAR_TOKEN=SetMe
