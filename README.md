 SwiftDeploy

A CLI deployment tool that uses a declarative YAML manifest as the single
source of truth for your entire infrastructure. Write one file — SwiftDeploy
generates all configs, builds the image, starts the stack, and manages
the container lifecycle.

 How It Works

You describe your deployment in `manifest.yaml`. SwiftDeploy reads that
file and generates `nginx.conf` and `docker-compose.yml` from templates.
Nothing is written by hand except the manifest.

If the generated files are deleted, running `swiftdeploy init` regenerates
them perfectly from the manifest.

 Project Structure
swiftdeploy/
manifest.yaml                    
swiftdeploy                      
Dockerfile                       
app/
main.py
   └── requirements.txt             
templates/
  ├── nginx.conf.template
  └── docker-compose.yml.template  
└── README.md


# Setup

#Prerequisites

- Docker Desktop installed and running
- Python 3 installed
- pyyaml installed: `pip3 install pyyaml`

 Installation

```bash
git clone https://github.com/Bukunmi0817/swiftdeploy.git
cd swiftdeploy
chmod +x swiftdeploy
```

#Subcommand Walkthrough

 init

Generates `nginx.conf` and `docker-compose.yml` from templates using
values from `manifest.yaml`.

```bash
./swiftdeploy init
```

Output:
Reading manifest...
Generating nginx.conf...
Generating docker-compose.yml...
Done. Generated files:
nginx.conf
docker-compose.yml

### validate

Runs 5 pre-flight checks before deploying. Exits non-zero on any failure.

```bash
./swiftdeploy validate
```

Checks:
1. manifest.yaml exists and is valid YAML
2. All required fields are present
3. Docker image exists locally
4. Nginx port is not already in use
5. Generated nginx.conf is syntactically valid

Output:
[✓] Check 1: PASSED
[✓] Check 2: PASSED
[✓] Check 3: PASSED
[✓] Check 4: PASSED
[✓] Check 5: PASSED
All checks passed. Ready to deploy.

### deploy

Runs init, builds the Docker image, starts the full stack, and blocks
until health checks pass or 60 second timeout.

```bash
./swiftdeploy deploy
```

Output:
Running init...
Building Docker image...
Starting stack...
Waiting for health checks to pass (timeout: 60s)...
Stack is healthy. Deploy complete.
Dashboard available at http://localhost:8080

### promote

Switches between stable and canary mode. Only restarts the app container
— nginx keeps running with zero downtime.

```bash
./swiftdeploy promote canary
./swiftdeploy promote stable
```

What promote does:
1. Updates mode in manifest.yaml
2. Regenerates docker-compose.yml with new MODE env var
3. Restarts only the app container
4. Waits for health check to pass
5. Confirms new mode by hitting /healthz

### teardown

Stops and removes all containers, networks, and volumes.

```bash
./swiftdeploy teardown
```

With --clean flag also deletes generated config files:

```bash
./swiftdeploy teardown --clean
```

## The API

The service runs on port 3000 internally. All traffic routes through
nginx on port 8080. The app port is never exposed directly.

### Endpoints

**GET /** — Welcome message with current mode, version, and timestamp

```json
{
  "message": "Welcome to SwiftDeploy",
  "mode": "stable",
  "version": "1.0.0",
  "timestamp": "2026-05-03T15:00:00+00:00"
}
```

**GET /healthz** — Liveness check with process uptime

```json
{
  "status": "healthy",
  "uptime": 3600
}
```

**POST /chaos** — Simulates degraded behaviour (canary mode only)

Slow mode:
```json
{ "mode": "slow", "duration": 5 }
```

Error mode:
```json
{ "mode": "error", "rate": 0.5 }
```

Recover:
```json
{ "mode": "recover" }
```

## The Manifest

All configuration lives in `manifest.yaml`:

```yaml
services:
  image: swift-deploy-1-node:latest
  port: 3000
  mode: stable
  version: "1.0.0"
  replicas: 1
  restart_policy: unless-stopped

nginx:
  image: nginx:latest
  port: 8080
  proxy_timeout: 30

network:
  name: swiftdeploy-net
  driver_type: bridge

volumes:
  logs: swiftdeploy-logs
```

To change any value — edit manifest.yaml and run `./swiftdeploy init`.
Both config files regenerate automatically.

## Security

- Containers run as non-root user (appuser)
- All Linux capabilities dropped (cap_drop: ALL)
- nginx.conf mounted read-only (:ro)
- App port never exposed to the internet
- Base image: python:3.11-slim (under 300MB)

## Stable vs Canary
canary carries a X-mode header on all request while stable does not
