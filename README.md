# Ansible playbooks to form a Galaxy/Slurm cloud

[![Build Status](https://travis-ci.com/InformaticsMatters/ansible-galaxy-cloud.svg?branch=master)](https://travis-ci.com/InformaticsMatters/ansible-galaxy-cloud)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)

This repo contains [Ansible] playbooks for deploying a compute cluster. The 
primary purpose is to act as a HPC resource for executing [Galaxy] and
[Nextflow] workflows. The playbooks can be used to spin up nodes on an
OpenStack cluster and deploy a [Slurm] environment to this. You can also
deploy [Pulsar] for executing Galaxy tools and Nextflow for running Nextflow
workflows. Both Pulsar and Nextflow use the Slurm cluster for execution.
The use of Pulsar allows Galaxy workflows to be executed without the need
for a shared filesystem between the Galaxy and Slurm environments.

>   **This project should not to be confused with Ansible Galaxy**, Ansible's
    community-driven repository of Ansible Roles.
     
Creating a complete cluster takes approx 15 mins depending on the number of
nodes.

Singularity is deployed to the Slurm cluster allowing jos to be run using
Singularity containers. Currently Pulsar is not configured to use Singularity
containers and instead deploys tool dependencies using `conda` but we aim to
switch to all execution using Singularity in the near future.

>   Deployment and configuration of Galaxy will be described elsewhere
    in the near future.

This `ansible-galaxy-cloud` project contains a [site.yaml](site.yaml) file and
_roles_ for the formation (and removal) of a [Nextflow]/[Slurm]/[MUNGE]/[Pulsar]
cluster, a cluster suitable for [Galaxy] that consists of a **head** node and
one or more **worker** nodes that share an NFS-mounted volume attached to
the head node (mounted as `/data`). 

>   As the cloud instances are unlikely to be accessibly from outside the
    provider network this playbook is expected to be executed from a 
    suitably equipped _bastion_ node on the cloud provider (OpenStack).

## Built-in applications
The following applications can be deployed to the cluster, each managed in
their own `app_` roles: -

-   [Nextflow]
-   [Slurm] (and [MUNGE])
-   [Pulsar]

Application components (nextflow, slurm, Pulsar) are deployed when their
corresponding `install` variable is set (see [group_vars/all/main.yaml](group_vars/all/main.yaml)).
The default in this repository is to enable and install all of them.
If you don't want to install a particular component (say nextflow), set its
`install` variable to `no`, i.e. `install_nextflow: no`.

## Deploying
You need to satisfy a few prerequisites before you can deploy the cluster
and applications, as detailed below.

### Prerequisite - a bastion node
You can use the [bastion] project to instantiate a suitable
Bastion instance from a workstation outside your cluster. From that
instance you should be able to create the cluster using the pre-configured
Python virtual environment that it creates there.

Create your bastion and ssh to it. You'll find a clone of this
repository in its `~/git` directory and you can continue reading this
document from there.

### Prerequisite - provider environment
You will need to set provider-specific environment variables before you
can run this playbook. If you're using OpenStack you should `source` the
keystone file provided by your stack provider. This sets up the essential
credentials to create and access cloud resources.

>   If you've used the [ansible-bastion] playbook it will have written a
    suitable set of authentication parameters for you in the root
    of the initial clone of this project so you need not source anything.

### Prerequisite - template environment
Inspect the [setenv-template.sh](setenv-template.sh) file in the root of the
project to see if there are any variables you need to define. Instructions for
providing these variables can be found in the template file.

### Prerequisite - playbook configuration
The playbook relies on a number of _roles_ in the project. Where appropriate,
each role exposes its key variables in a corresponding `defaults/main.yaml`
file but the main (common) variables have been placed in
[group_vars/all/main.yaml](group_vars/all/main.yaml).

At the very least you should provide your own values for: -

-   `instance_base_name`. A tag prepended to the cloud objects created
    (instances and volumes)
-   `head_addr`. The IP address (from a pool you own) to assign to the
    head node.
-   `worker_count`. The number of worker instances that will be put in the
    cluster.

>   You are encouraged to review all the variables so that you can decide
    whether you need to provide your own values for any of them.  

The easiest way to over-ride the built-in values is to provide your
own YAML-based [parameters] file (called `parameters`). The project
`parameters` file is excluded from the repository using `.gitignore`.
To define your own shared volume size you could provide the following in
a `parameters` file: -

    volume_size_g: 3000

...and add the file to your Ansible command-line using
`--extra-vars "@parameters"`

### Installing public SSH keys
Any `.pub` files fopund in the project's root directory will be considered
public SSH key-files and they will be added to the `centos` account of the
head node, allowing those users access to it.
  
## Running the playbook
With environment variables set and a `parameters` file written,
run the following on a suitably equipped bastion on your cloud provider: -

    $ pip install --upgrade pip
    $ pip install -r requirements.txt
    $ ansible-playbook site.yaml --extra-vars "@parameters"

>   You can avoid formatting the shared volume (for instance if
    you have an existing non-ext4 volume) by adding `volume_initialise: no`
    to your parameters file. By default the volume is expected to
    be an `ext4` volume.
    
>   CAUTION: The instance creation process creates instances and volumes whose
    names begin with the value of the `instance_base_name` variable. Use a
    base name that is unique to your cluster or, on deletion, you may find
    you've lost more than you expected!

And, to destroy the cluster: -

    $ ansible-playbook unsite.yaml --extra-vars "@parameters"

>   To avoid deleting the shared volume, add `volume_delete: no` to your
    parameters file. By default it is deleted when the cluster is deleted.
    
---

[ansible]: https://www.ansible.com/
[bastion]: https://github.com/InformaticsMatters/ansible-bastion
[galaxy]: https://docs.galaxyproject.org/en/latest/index.html
[munge]: https://dun.github.io/munge/
[nextflow]: https://www.nextflow.io
[parameters]: https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#passing-variables-on-the-command-line
[pulsar]: https://pulsar.readthedocs.io/en/latest/index.html
[slurm]: https://slurm.schedmd.com/documentation.html
