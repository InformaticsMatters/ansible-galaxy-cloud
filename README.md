# Ansible playbooks to form a Galaxy/Slurm cloud

This repo contains [Ansible] playbooks for deploying a compute cluster. The 
primary purpose is to act as a HPC resource for executing [Galaxy] and [Nextflow]
workflows. The playbooks can be used to spin up nodes on an OpenStack cluster
and deploy a [Slurm] environment to this. You can also deploy [Pulsar] for executing
Galaxy tools and Nextflow for running Nextflow workflows. Both Pulsar and Nextflow
use the Slurm cluster for execution. The use of Pulsar allows Galaxy workflows to be executed
without the need for a shared filesystem between the Galaxy and Slurm environments.

Creating a complete cluster takes approx 15 mins depending on the number of nodes.

Singularity is deployed to the Slurm cluster allowing jos to be run using Singularity
containers. Currently Pulsar is not configured to use Singularity containers and instead
deploys tool dependencies using `conda` but we aim to switch to all execution using Singularity
in the near future.

Deployment and configuration of Galaxy will be described elsewhere in the near future.

This `ansible-galaxy-cloud` project contains a `site.yaml` file and _roles_
for the formation (and removal) of a [nextflow]/[slurm]/[MUNGE]/[Pulsar]
cluster suitable for [Galaxy] that consists of a **head** node and one or
more **worker** nodes that share an NFS-mounted volume attached to
the head node (mounted as `/data`). 

>   As the cloud instances are unlikely to be accessibly from outside the
    provider network this playbook is expected to be executed from a 
    suitably equipped _bastion_ node on the cloud provider (OpenStack).

## The bastion node
You can use the [bastion] project to instantiate a suitable
Bastion instance from a workstation outside your cluster. From that
instance you should be able to create the cluster using the pre-configured
Python virtual environment that it creates there.

Create your bastion and ssh to it. You'll find a clone of this
repository in its `~/git` directory and you can continue reading this
document from there.

## Provider environment
You will need to set provider-specific environment variables before you
can run this playbook. If you're using OpenStack you should `source` the
keystone file provided by your stack provider. This sets up the essential
credentials to create and access cloud resources.

## Template environment
Inspect the `setenv-template.sh` file in the root of the project to see
if there are any variables you need to define. Instructions can be found in
the template file.

## Playbook configuration
The playbook relies on a number of _roles_ in the project. Where appropriate,
each role exposes its key variables in a corresponding `defaults/main.yaml`
file but the main (common) variables have been placed in
`group_vars/all/main.yaml`.

At the very least you should provide your own values for: -

-   `instance_base_name`. A tag prepended to the cloud objects created
    (instances and volumes)
-   `head_addr`. The IP address (from a pool you own) to assign to the
    head node.
-   `worker_count`. The number of worker instances that will be put in the
    cluster.

>   Feel free to review all the variables so that you can decide whether
    you'd like to provide your own values for them.  

>   Application components (nextflow, slurm, Pulsar) are deployed when their
    corresponding `install_` variable is set. The default in this repository
    is to enable and install all of them. If you don't want to install
    a particular component (say nextflow) set its `install_` variable to `no`,
    i.e. `install_nextflow: no`.

The easiest way to over-ride the built-in values is to provide your
own YAML-based [parameters] file called `parameters`. The project `parameters`
file is excluded from the repository using `.gitignore`.
    
## Running the playbook
With environment variables set and a `parameters` file written,
run the following on a suitably equipped bastion on your cloud provider: -

    $ pip install -r requirements.txt
    $ ansible-playbook site.yaml --extra-vars "@parameters"

And, to destroy the cluster: -

    $ ansible-playbook unsite.yaml --extra-vars "@parameters"

---

[galaxy]: https://docs.galaxyproject.org/en/latest/index.html
[bastion]: https://github.com/InformaticsMatters/ansible-bastion
[munge]: https://dun.github.io/munge/
[nextflow]: https://www.nextflow.io
[parameters]: https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#passing-variables-on-the-command-line
[pulsar]: https://pulsar.readthedocs.io/en/latest/index.html
[slurm]: https://slurm.schedmd.com/documentation.html
[ansible]: https://www.ansible.com/
