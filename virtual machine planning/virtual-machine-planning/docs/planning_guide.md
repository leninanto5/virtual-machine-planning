# VM Planning Guide

This guide explains how `vm_planning.py` decides how many virtual machines (VMs) and physical hosts a set of workloads needs.

## 1. Inputs
Each workload is described by:

| Field | Meaning |
|---|---|
| `name` | Workload name (e.g. Web Server) |
| `vcpu` | vCPUs needed by ONE instance |
| `ram_gb` | RAM (GB) needed by ONE instance |
| `storage_gb` | Disk (GB) needed by ONE instance |
| `count` | Number of instances |

See `sample_workloads.json` for an example.

## 2. VM size catalog
| Size | vCPU | RAM (GB) |
|---|---|---|
| small | 1 | 2 |
| medium | 2 | 4 |
| large | 4 | 8 |
| xlarge | 8 | 16 |
| 2xlarge | 16 | 32 |
| 4xlarge | 32 | 64 |

## 3. Planning steps
1. **Add headroom.** Required vCPU and RAM are increased by a safety buffer (default 20%) so the VM never runs at 100%.
2. **Pick the smallest VM size** that fits both the vCPU and RAM requirement. If even the largest size is too small, several VMs are used for that instance.
3. **Total the resources** allocated across all VMs.
4. **Calculate utilization** = actual requirement / allocated resources. Low utilization means the VM size is oversized for the workload.
5. **Plan physical hosts** using CPU overcommit (default 4 vCPU per physical core) and RAM at 1:1, then add one extra host for redundancy (N+1).

## 4. Formulas
```
Required vCPU = vcpu x (1 + headroom)
Required RAM  = ram_gb x (1 + headroom)
Hosts (CPU)   = ceil(total allocated vCPU / (host cores x overcommit))
Hosts (RAM)   = ceil(total allocated RAM / host RAM)
Hosts needed  = max(Hosts CPU, Hosts RAM) + 1
```

## 5. Tips
- Use 10-20% headroom for stable workloads and 30-40% for spiky ones.
- Keep database servers at low CPU overcommit.
- Review workloads with utilization below 40% and consider a smaller size.
