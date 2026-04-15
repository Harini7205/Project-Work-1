# EHR Phase 1 — DQN Leader Election with Real Metrics

## What this does

4 hospital Docker containers each expose real CPU, memory,
latency, and error-rate metrics. Prometheus scrapes them every 10s.
The DQN AI agent reads those metrics and elects the best leader node,
printing exactly WHY it chose that hospital.

## Prerequisites

Only one thing needed: **Docker Desktop running**.
Open Docker Desktop and wait until it says "Docker Desktop is running".

## How to run (2 commands)

```bash
# In your terminal, go into the project folder:
cd phase1

# Start everything:
docker compose up --build
```

That's it. Wait about 60 seconds for all containers to start.

## What you will see

In the terminal where you ran docker compose, you'll see output like:

```
══════════════════════════════════════════════════════════════
  ELECTION ROUND 3
══════════════════════════════════════════════════════════════

  Hospital      CPU%   Mem%   Lat ms  ErrRate   PoRI Score
  ────────────────────────────────────────────────────────
  hospitalA    52.3%  61.0%    88.2    0.055       0.5821
  hospitalB    14.1%  61.0%    19.4    0.012       0.8901   ← best
  hospitalC    78.4%  61.0%   142.3    0.089       0.2944
  hospitalD    31.2%  61.0%    54.8    0.031       0.7102

  DQN Q-values (higher = DQN prefers this node):
  Hospital      Q-value   Confidence
  ────────────────────────────────────────────────
  hospitalA      0.3821   ████░░░░░░░░░░░░
  hospitalB      0.9134   ████████████████  ← ELECTED
  hospitalC     -0.2104   ████░░░░░░░░░░░░
  hospitalD      0.6291   ██████████░░░░░░

  ✅  ELECTED LEADER: HOSPITALB

  WHY hospitalB was chosen:
    • PoRI Score:  0.8901  (highest in network)
    • CPU usage:   14.1%   → LOW — has capacity
    • Latency:     19.4 ms → FAST — can prove quickly
    • Error rate:  0.012   → RELIABLE
    • Memory:      61.0%

  Runner-up: hospitalD  (PoRI 0.7102, gap = 0.1799)

  🧠  DQN Training:
    • Loss:     0.002341
    • Epsilon:  0.8234    (still exploring)
    • Rounds:   3

  Next election in 30s...
```

## Useful commands (open a new terminal tab)

```bash
# See all running containers:
docker ps

# Watch AI agent output live:
docker logs ai-agent -f

# See hospital B metrics:
curl http://localhost:8002/metrics/json

# Open Prometheus dashboard in browser:
open http://localhost:9090

# In Prometheus, try these queries:
#   hospital_cpu_percent
#   hospital_avg_latency_ms
#   hospital_error_rate
```

## Stop everything

```bash
docker compose down
```

## Understanding the output

### PoRI Score
Higher = better leader. Calculated as:
  score = 1 - (0.40 × latency + 0.30 × cpu + 0.20 × error_rate + 0.10 × memory)

### Q-values
What the DQN neural network learned about each hospital.
Higher Q-value = DQN thinks electing this node gives a better reward.
Early rounds are random (epsilon high). After ~10 rounds the DQN
starts confidently picking the same best node every time.

### Epsilon
Starts at 1.0 (fully random) and decays toward 0.05 (mostly exploiting).
This is how DQN learns — it tries random choices first, learns which
gives better rewards, then starts committing to the best choice.

## File structure

```
phase1/
├── hospital-node/
│   ├── server.py          ← real metrics server (runs on all 4 hospitals)
│   ├── requirements.txt
│   └── Dockerfile
├── prometheus/
│   └── prometheus.yml     ← scrapes all 4 hospitals every 10s
├── ai-agent/
│   ├── agent.py           ← DQN election logic
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yaml    ← wires everything together
└── README.md
```
