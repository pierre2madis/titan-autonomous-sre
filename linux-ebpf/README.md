# TITAN Linux/eBPF Observability & RCA

Bash-first Linux observability and root-cause analysis.

## CPU v0.1.0

Components:
- Synthetic CPU evidence replay
- Prometheus-format metrics
- Grafana CPU dashboard

## CPU-01 — Synthetic Replay

Run from the repository root:

    ./linux-ebpf/simulators/cpu/cpu_replay_v0_1.sh /tmp/titan-cpu-replay-demo

The replay generates synthetic JSON and Prometheus evidence.

It does not create CPU load, modify monitoring services,
or publish operational metrics.

## Grafana

Dashboard:

    linux-ebpf/dashboards/grafana/titan_cpu_overview_v0_1.json

The dashboard currently queries real CPU metrics.
Synthetic replay metrics use a separate titan_demo_* namespace.

## Limitations

- No real CPU fault injection yet
- No verified process-level root cause
- No measured service SLO
- No automatic remediation

## Roadmap

CPU -> Memory -> Disk I/O -> Network -> SLO -> RCA -> Remediation
