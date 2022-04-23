# SysBindings Daemon

Little toolkit for control the sysctl/sysfs bindings on Kubernetes Cluster on the fly
and without unnecessary restarts of cluster or node pool. Allows to control managed
and/or own-architected and/or own-managed clusters because uses only well-known
techniques.

## Helm chart

You are welcome to try our official Helm Registry!

```bash
helm repo add wallarm https://charts.wallarm.com
helm repo update
helm search repo wallarm/sysbindings -l
```

## CLI

See `sysbindings --help` for details:

```bash
usage: sysbindings [-h] [--config CONFIG] [--oneshot] [--loglevel LOGLEVEL]

Little toolkit for control the sysctl/sysfs bindings on Kubernetes Cluster on the flyand
without unnecessary restarts of cluster or node pool. Allows to control managed and/or
own-architected and/or own-managed clusters because uses only well-knowntehniques.

optional arguments:
  -h, --help           show this help message and exit
  --config CONFIG      use specified configuration file
  --oneshot            just apply configuration and exit, no daemonize
  --loglevel LOGLEVEL  log verbosity: DEBUG, INFO, WARNING or ERROR
```

## Configuration

See detailed example in the `sysbindings.yaml` file.

## Environment

Use this environment variables for configuring script:

```bash
LOGLEVEL=INFO
SYSBINDINGS_CONFIG=/opt/sysbindings/sysbindings.yaml
```

See details in the `sysbindings.yaml` file.

## Arguments Priority

CLI arguments have maximal priority, ENVs is secondary and config entries
just final.
