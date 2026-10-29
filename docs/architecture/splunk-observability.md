# TITAN — Splunk Observability Architecture

## Overview

TITAN is an evolving, laboratory-validated Autonomous SRE reference project. This module documents a working telemetry path from Splunk Enterprise and the OpenTelemetry Collector host into Prometheus and Grafana. It is intended as a reproducible starting point for Splunk administrators and SREs, not as a production-certified deployment.

## Architecture

```text
Splunk Enterprise (Cluster Manager)
        | Splunk management REST API
        v
OpenTelemetry Collector ----------------------+
  splunk_enterprise receiver                 |
  resource/splunk -> batch                   |
        |                                    |
        +--> prometheus_remote_write         |
                                             |
Collector Linux host                         |
  hostmetrics receiver                       |
  resource/host -> batch                     |
        |                                    |
        +--> prometheus_remote_write --------+
                       |
                       v
           Prometheus Remote Write Receiver
                       |
                       | PromQL
                       v
                 Grafana Dashboard
```

The Splunk and host receivers feed **separate metrics pipelines**, allowing operators to distinguish the Splunk service from the Linux server running the Collector. Both pipelines were also configured with a debug exporter during validation.

## Validated Telemetry

### Splunk health

The `splunk_enterprise` receiver retrieves health data from the Splunk Cluster Manager through the Splunk management API. The validated metric family is `splunk_health`, with **28 observed time series**. These are health observations, **not automatically confirmed incidents**. In a constrained lab, intentional shutdowns and maintenance must be considered before generating alerts.

The validated Prometheus source labels are:

- `job="titan-splunk-cluster"`
- `instance="us02"`

### Collector host

The `hostmetrics` receiver collects CPU, memory, filesystem, disk I/O, and network metrics from the **Collector host only**. It does not automatically cover the Splunk indexers or Search Heads. The validated source labels are:

- `job="titan-otel-host"`
- `instance="splunk-otel"`

Twenty host metric families were observed, including `system_cpu_time_seconds_total`, `system_memory_usage_bytes`, `system_filesystem_usage_bytes`, and network/disk counters.

## Data Flow and Source Identity

The Collector exports metrics to a Prometheus Remote Write Receiver. Resource-to-telemetry conversion is enabled to retain useful resource identity on exported metrics. Verify labels in Prometheus before adapting queries to a different deployment.

Illustrative queries against the validated lab labels:

```promql
count(splunk_health{job="titan-splunk-cluster",instance="us02"})
```

```promql
count(system_memory_usage_bytes{job="titan-otel-host",instance="splunk-otel"})
```

These queries are examples of **metric presence**, not service availability SLIs.

## Grafana Dashboard v1.0.0

The first TITAN Grafana dashboard was imported and visually checked: **16 of 16 panels displayed data**. The panels cover Splunk health, CPU, memory, filesystem, disk, network, and telemetry freshness.

**Known review items before a polished public dashboard release:**

- Correct health-status color and threshold semantics.
- Validate memory-utilization calculations against the metric's state semantics.
- Use rates for cumulative CPU-time and network/disk counters where appropriate.
- Document network-interface filtering and expected lab states.

The dashboard JSON is a separate deliverable; this document does not claim that it is already committed to the repository.

## Deployment and Operational Validation

The lab integration was validated through:

1. Offline Collector configuration validation.
2. Backup of the active Collector configuration before deployment.
3. Controlled deployment and restart of **only** the Collector service.
4. Collector readiness verification.
5. Prometheus metric discovery and source-label verification.
6. Grafana import and visual inspection.

The portable OpenTelemetry Collector example has passed offline configuration validation against Splunk OpenTelemetry Collector v0.163.1 and is prepared for publication alongside this document. Production deployment instructions remain outside the scope of this release.

## Security Guidance

- Do not commit credentials, API tokens, private keys, or environment secret files.
- Use valid certificates and enforce TLS verification in production.
- Restrict access to Splunk management APIs and telemetry endpoints.
- Replace lab-specific addresses, usernames, and filesystem paths in shared examples.
- Treat any lab-only TLS verification bypass as an exception, not a recommended default.

## Scope and Roadmap

**Validated now:** Cluster Manager health telemetry; Collector-host infrastructure metrics; Prometheus Remote Write ingestion; Grafana visualization.

**Planned or pending validation:** Search Head Cluster and indexer monitoring; node_exporter and TITAN Evidence Engines; SLO/SLI dashboards, error budgets and burn rates; evidence-based incident correlation and remediation visibility.

A health metric, host-utilization graph, or telemetry freshness panel must not be presented as a validated business SLO without an appropriate service-level measurement contract.

## Status

**Reference implementation — laboratory validated; documentation candidate.** No production readiness certification is implied.
