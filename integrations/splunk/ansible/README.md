# Splunk Distributed Search over Tailscale

## Problem

Splunk Search Heads and indexers were deployed across two physical
VirtualBox hosts.

Indexer cluster peers advertised management addresses from a VirtualBox
host-only network that was not reachable from the Search Heads.

Symptoms included:

- DistributedPeerManagerHeartbeat connection failures
- "No route to host" on TCP 8089
- Distributed searches returning no remote indexer events

## Root Cause

The indexers registered search addresses belonging to a VirtualBox
host-only network inaccessible from the Search Head Cluster.

## Solution

Configure `register_search_address` in the `[clustering]` section
of each indexer's `server.conf`.

Use a reachable Tailscale address for distributed search management
connectivity while preserving existing replication networking.

## Deployment

Requirements:

- Splunk Enterprise indexer cluster
- Ansible
- community.general collection
- TCP 8089 connectivity from Search Heads to indexers

Copy `inventory/lab.ini.example` to a private inventory and configure
the corresponding host variables.

Run the configuration check:

    ansible-playbook \
      -i inventory/lab.ini \
      playbooks/configure_search_address.yml \
      --check

Apply configuration changes only after review.

Configuration changes may require a controlled indexer restart.

## Validation

The laboratory validation confirmed:

- Three indexers participating in distributed search
- Replication factor met
- Search factor met
- All indexers UP and searchable
- Successful ingestion from Heavy Forwarder hf01
- Successful event retrieval from Search Head shc01

## Security

Do not commit credentials, private keys, production inventory files,
Splunk secrets, or complete server.conf files.

## Operational Notes

The indexer cluster was restarted using Splunk's native searchable
rolling restart procedure after verifying cluster readiness.

The operational Ansible project remains separate from the public
Git repository.
