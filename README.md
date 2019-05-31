# Ansible playbooks to form the graph-processing cloud
The `graph-cloud` project contains a `site.yaml` file and _roles_
for the formation (and removal) of a [nextflow]/[slurm]/[MUNGE]/[Pulsar]
graph-processing cluster that consists of a **head** node and one or
more **worker** nodes that share an NFS-mounted volume attached to
the head node.

>   As the cloud instances are unlikely to be accessibly from outside the
    provider network this playbook is expected to be executed from a 
    suitably equipped _bastion_ node on the cloud provider (OpenStack).

## The bastion node
You can use the [graph-bastion] project to instantiate a suitable
Bastion instance from a workstation outside your cluster. From that
instance you should be able to create the cluster using the pre-configured
Python virtual environment that it creates there.

Create your bastion, login to it and clone this repository into it's `~/git`
directory and then continue reading from there...

## Playbook configuration
The playbook relies on a number of _roles_ in the project. Where appropriate,
each role exposes its key variables in a corresponding `defaults/main.yaml`
file but the main (common) variables have been placed in
`group_vars/all/main.yaml`.

Some _sensitive_ configuration is extracted from
environment variables on the playbook host (bastion).

At the very least you should provide your own values for: -

-   `instance_base_name`. A tag prepended to the cloud objects created
    (instances and volumes)
-   `head_addr`. The IP address (from a pool you own) to assign to the
    head node.
-   `worker_count`. The number of worker instances that will be put in the
    cluster.

>   Feel free to review all the variables so that you can decide whether
    you'd like to provide your own values for them.  

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

## Post-install Galaxy actions
At the moment some steps appear to be required to allow the cluster to
be used from Galaxy. For the time-being they remain a _manual_
post-installation step until we understand what needs to be done in the
long-term.

From the _head_ node run the following as the `pulsar` user: -

    $ dependencies/_conda/bin/conda create \
        --name __autodock-vina@1.1.2 autodock-vina==1.1.2 \
        --channel bioconda

---

[graph-bastion]: https://github.com/InformaticsMatters/graph-bastion
[munge]: https://dun.github.io/munge/
[nextflow]: https://www.nextflow.io
[parameters]: https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#passing-variables-on-the-command-line
[pulsar]: https://pulsar.readthedocs.io/en/latest/index.html
[slurm]: https://slurm.schedmd.com/documentation.html
