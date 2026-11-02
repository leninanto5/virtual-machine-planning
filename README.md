# Virtual Machine Planning

A Python command-line tool that plans how many **virtual machines (VMs)** and **physical hosts** are needed to run a set of workloads. It picks the right VM size for each workload, adds a safety buffer, shows resource utilization, and calculates the physical servers required with redundancy.

## Features
- Automatic VM size selection (small to 4xlarge)
- Configurable headroom (safety buffer) for CPU and RAM
- CPU and RAM utilization for every workload
- Suggestions for oversized VMs
- Physical host calculation with CPU overcommit and N+1 redundancy
- Interactive mode, JSON file input, or built-in demo
- Export the plan to a CSV file

## Tech Stack
- Python 3
- tabulate (table output)
- JSON, CSV

## Project Structure
```
virtual-machine-planning/
├── docs/
│   ├── planning_guide.md       # how the planning works
│   └── sample_workloads.json   # example input
├── vm_planning.py              # main program
├── requirements.txt
└── README.md
```

## How to Run

1. Clone the repository
```bash
git clone https://github.com/leninanto5/virtual-machine-planning.git
cd virtual-machine-planning
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run the demo
```bash
python vm_planning.py --demo
```

4. Run in interactive mode
```bash
python vm_planning.py
```

5. Run with your own JSON file
```bash
python vm_planning.py --file my_workloads.json --headroom 25 --export
```

## Arguments
| Argument | Description | Default |
|---|---|---|
| `--file` | JSON file with workloads | interactive mode |
| `--demo` | Use `docs/sample_workloads.json` | off |
| `--headroom` | Safety buffer in percent | 20 |
| `--host-cores` | CPU cores per physical host | 64 |
| `--host-ram` | RAM (GB) per physical host | 256 |
| `--overcommit` | vCPU per physical core | 4 |
| `--export` | Save plan to `docs/vm_plan.csv` | off |

## Input Format
```json
[
  {"name": "Web Server", "vcpu": 2, "ram_gb": 4, "storage_gb": 50, "count": 3}
]
```

## Planning Formulas
```
Required vCPU = vcpu x (1 + headroom)
Required RAM  = ram_gb x (1 + headroom)
Hosts (CPU)   = ceil(total vCPU / (host cores x overcommit))
Hosts (RAM)   = ceil(total RAM / host RAM)
Hosts needed  = max(Hosts CPU, Hosts RAM) + 1
```

More details are in `docs/planning_guide.md`.

## Author
**Leninanto**
GitHub: [leninanto5](https://github.com/leninanto5)
