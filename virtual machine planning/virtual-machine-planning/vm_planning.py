import argparse
import csv
import json
import math
import os

from tabulate import tabulate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILE = os.path.join(BASE_DIR, "docs", "sample_workloads.json")
EXPORT_FILE = os.path.join(BASE_DIR, "docs", "vm_plan.csv")

# (size name, vCPU, RAM in GB)
VM_CATALOG = [
    ("small", 1, 2),
    ("medium", 2, 4),
    ("large", 4, 8),
    ("xlarge", 8, 16),
    ("2xlarge", 16, 32),
    ("4xlarge", 32, 64),
]

REQUIRED_FIELDS = ("name", "vcpu", "ram_gb", "storage_gb", "count")


# ---------------------------------------------------------------- loading
def load_workloads(path):
    with open(path, "r", encoding="utf-8") as f:
        workloads = json.load(f)
    for w in workloads:
        validate_workload(w)
    return workloads


def validate_workload(w):
    missing = [field for field in REQUIRED_FIELDS if field not in w]
    if missing:
        raise ValueError(f"Workload is missing fields: {', '.join(missing)}")
    for field in REQUIRED_FIELDS[1:]:
        if w[field] <= 0:
            raise ValueError(f"'{field}' must be greater than 0 in workload '{w['name']}'")


# --------------------------------------------------------------- planning
def choose_vm(req_vcpu, req_ram):
    """
    Returns (size, vm_vcpu, vm_ram, vms_per_instance).
    Picks the smallest VM that fits; if none fits, uses several of the largest.
    """
    for size, cpu, ram in VM_CATALOG:
        if cpu >= req_vcpu and ram >= req_ram:
            return size, cpu, ram, 1

    size, cpu, ram = VM_CATALOG[-1]
    vms = max(math.ceil(req_vcpu / cpu), math.ceil(req_ram / ram))
    return size, cpu, ram, vms


def plan_workload(w, headroom):
    factor = 1 + headroom / 100
    req_vcpu = w["vcpu"] * factor
    req_ram = w["ram_gb"] * factor

    size, vm_cpu, vm_ram, per_instance = choose_vm(req_vcpu, req_ram)
    total_vms = per_instance * w["count"]

    alloc_vcpu = total_vms * vm_cpu
    alloc_ram = total_vms * vm_ram
    used_vcpu = w["vcpu"] * w["count"]
    used_ram = w["ram_gb"] * w["count"]

    return {
        "workload": w["name"],
        "count": w["count"],
        "vm_size": size,
        "vms": total_vms,
        "alloc_vcpu": alloc_vcpu,
        "alloc_ram": alloc_ram,
        "storage_gb": w["storage_gb"] * w["count"],
        "cpu_util": round(used_vcpu / alloc_vcpu * 100, 1),
        "ram_util": round(used_ram / alloc_ram * 100, 1),
    }


def plan_hosts(total_vcpu, total_ram, host_cores, host_ram, overcommit):
    hosts_cpu = math.ceil(total_vcpu / (host_cores * overcommit))
    hosts_ram = math.ceil(total_ram / host_ram)
    base = max(hosts_cpu, hosts_ram)
    return {
        "hosts_cpu": hosts_cpu,
        "hosts_ram": hosts_ram,
        "hosts_needed": base + 1,  # N+1 redundancy
        "bottleneck": "CPU" if hosts_cpu >= hosts_ram else "RAM",
    }


def build_plan(workloads, headroom, host_cores, host_ram, overcommit):
    rows = [plan_workload(w, headroom) for w in workloads]
    totals = {
        "vms": sum(r["vms"] for r in rows),
        "vcpu": sum(r["alloc_vcpu"] for r in rows),
        "ram": sum(r["alloc_ram"] for r in rows),
        "storage": sum(r["storage_gb"] for r in rows),
    }
    hosts = plan_hosts(totals["vcpu"], totals["ram"], host_cores, host_ram, overcommit)
    return rows, totals, hosts


# ---------------------------------------------------------------- output
def print_plan(rows, totals, hosts, args):
    headers = ["Workload", "Instances", "VM Size", "Total VMs",
               "vCPU", "RAM (GB)", "Storage (GB)", "CPU Util %", "RAM Util %"]
    table = [
        [r["workload"], r["count"], r["vm_size"], r["vms"], r["alloc_vcpu"],
         r["alloc_ram"], r["storage_gb"], r["cpu_util"], r["ram_util"]]
        for r in rows
    ]
    print(f"\nVM Plan (headroom {args.headroom}%)")
    print(tabulate(table, headers=headers, tablefmt="grid"))

    print("\nTotals")
    print(f"  Total VMs        : {totals['vms']}")
    print(f"  Total vCPU       : {totals['vcpu']}")
    print(f"  Total RAM        : {totals['ram']} GB")
    print(f"  Total storage    : {totals['storage']} GB")

    print("\nPhysical host plan")
    print(f"  Host size        : {args.host_cores} cores, {args.host_ram} GB RAM")
    print(f"  CPU overcommit   : {args.overcommit}:1")
    print(f"  Hosts for CPU    : {hosts['hosts_cpu']}")
    print(f"  Hosts for RAM    : {hosts['hosts_ram']}")
    print(f"  Bottleneck       : {hosts['bottleneck']}")
    print(f"  Hosts needed     : {hosts['hosts_needed']} (includes 1 spare for redundancy)")

    low = [r["workload"] for r in rows if r["cpu_util"] < 40 and r["ram_util"] < 40]
    if low:
        print(f"\nSuggestion: these workloads use under 40% of their VMs, review their size: {', '.join(low)}")


def export_csv(rows, path=EXPORT_FILE):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nPlan saved to {path}")


# ----------------------------------------------------------- user input
def ask(prompt, cast=float, minimum=0.0, default=None):
    while True:
        text = f"{prompt}" + (f" [{default}]" if default is not None else "") + ": "
        value = input(text).strip()
        if value == "" and default is not None:
            return default
        try:
            number = cast(value)
            if number <= minimum:
                print(f"  Enter a value greater than {minimum}.")
                continue
            return number
        except ValueError:
            print("  Enter a valid number.")


def interactive_workloads():
    print("=== Virtual Machine Planning ===")
    workloads = []
    while True:
        print(f"\nWorkload #{len(workloads) + 1}")
        name = input("Name (e.g. Web Server): ").strip() or f"Workload {len(workloads) + 1}"
        workloads.append({
            "name": name,
            "vcpu": ask("vCPUs needed per instance", int),
            "ram_gb": ask("RAM (GB) needed per instance", float),
            "storage_gb": ask("Storage (GB) per instance", float),
            "count": ask("Number of instances", int, default=1),
        })
        if input("Add another workload? (y/n) [n]: ").strip().lower() != "y":
            return workloads


def parse_args():
    p = argparse.ArgumentParser(description="Plan virtual machines and physical hosts for your workloads.")
    p.add_argument("--file", help="JSON file with workloads")
    p.add_argument("--demo", action="store_true", help="use docs/sample_workloads.json")
    p.add_argument("--headroom", type=float, default=20, help="safety buffer in percent (default 20)")
    p.add_argument("--host-cores", type=int, default=64, help="CPU cores per physical host (default 64)")
    p.add_argument("--host-ram", type=int, default=256, help="RAM in GB per physical host (default 256)")
    p.add_argument("--overcommit", type=float, default=4, help="vCPU per physical core (default 4)")
    p.add_argument("--export", action="store_true", help="save the plan to docs/vm_plan.csv")
    return p.parse_args()


def main():
    args = parse_args()

    if args.file:
        workloads = load_workloads(args.file)
    elif args.demo:
        workloads = load_workloads(SAMPLE_FILE)
    else:
        workloads = interactive_workloads()

    rows, totals, hosts = build_plan(
        workloads, args.headroom, args.host_cores, args.host_ram, args.overcommit
    )
    print_plan(rows, totals, hosts, args)

    if args.export:
        export_csv(rows)


if __name__ == "__main__":
    main()
