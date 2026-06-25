# SSH_HoneyPot

A modular, graphic-based honeypot to capture IP addresses, usernames, passwords, and commands from various protocols (SSH & HTTP supported). Written in Python.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Logging](#logging)
- [Honeypot Types](#honeypot-types)
- [Dashboard](#dashboard)
- [Docker](#docker)
- [VPS Hosting](#vps-hosting)
- [Running in Background With Systemd](#running-in-background-with-systemd)
- [Future Features](#future-features)
- [Helpful Resources](#helpful-resources)

---

## Installation

**1. Clone the repository.**

```bash
git clone https://github.com/TS1-L/SSH_HoneyPot.git
```

**2. Set permissions.**

Move into the `SSH_HoneyPot` folder and ensure `honeypy.py` has proper permissions:

```bash
cd SSH_HoneyPot
chmod 755 honeypy.py
```

**3. Generate SSH host key.**

Create the `staticf` directory and move into it:

```bash
mkdir staticf
cd staticf
```

An RSA key must be generated for the SSH server host key. Ensure the key is titled `server.key` and resides in the `staticf` directory:

```bash
ssh-keygen -t rsa -b 2048 -f server.key
```

---

## Usage

To provision a new instance of SSH_HoneyPot, use the `honeypy.py` file.

SSH_HoneyPot requires a bind IP address (`-a`) and a network port (`-p`). Use `0.0.0.0` to listen on all network interfaces. The protocol type must also be specified.

```
-a / --address    Bind address
-p / --port       Port
--ssh             SSH honeypot mode
--http            HTTP honeypot mode
```

**Example:**

```bash
python3 honeypy.py -a 0.0.0.0 -p 22 --ssh
```

> **Note:** If SSH_HoneyPot is configured to listen on a privileged port (e.g., 22), it must be run with `sudo` or root privileges. No other services should be using the specified port.

If port 22 is already in use as the system SSH port, it must be changed first. Refer to Hostinger's [How to Change the SSH Port](https://www.hostinger.com/tutorials/how-to-change-ssh-port-vps) guide.

> **Note:** To run with `sudo`, the root account must have access to all Python libraries. Install dependencies under the root user by switching to the root account and running:
>
> ```bash
> pip install -r requirements.txt
> ```
>
> This installs packages globally and is not considered best practice.

### Optional Arguments

A username (`-u`) and password (`-w`) can be specified to authenticate the SSH server. The default configuration accepts all usernames and passwords.

```
-u / --username   Username
-w / --password   Password
-t / --tarpit     Trap SSH sessions with an endless banner (SSH only)
```

**Example:**

```bash
python3 honeypy.py -a 0.0.0.0 -p 22 --ssh -u admin -w admin --tarpit
```

---

## Logging

SSH_HoneyPot maintains three log files located in `SSH_HoneyPot/log_files/`:

| Log File | Description |
|---|---|
| `cmd_audits.log` | Captures IP address, username, password, and all commands entered |
| `creds_audits.log` | Captures IP address, username, and password (comma-separated) — tracks SSH connection attempts |
| `http_audit.log` | Captures IP address, username, and password from HTTP attempts |

---

## Honeypot Types

SSH_HoneyPot is built with modularity in mind to support additional protocol types in the future (Telnet, HTTPS, SMTP, etc.). Currently, two honeypot types are supported.

### SSH

Emulates a basic shell environment. Use the usage instructions above to provision an SSH-based honeypot.

> **Tarpit (`-t / --tarpit`):** A tarpit slows down or delays brute-force login attempts. A very long SSH banner is sent to the connecting session — the only way to exit is by closing the terminal.

### HTTP

Using Python Flask, SSH_HoneyPot impersonates a default WordPress `wp-admin` login page and collects username/password pairs.

Default accepted credentials are `admin` / `deeboodah`, which redirect to a Rick Roll. Credentials can be customized using the `-u` and `-w` flags.

The HTTP honeypot runs on port `5000` by default, which can be changed with the `-p` flag.

> **Note:** Dashboard support for HTTP-based results is planned as a future addition.

---

## Dashboard

SSH_HoneyPot includes a `web_app.py` file for visualizing captured data. Run it in a separate terminal on localhost to view statistics including top 10 IP addresses, usernames, passwords, and commands in tabular format.

> The dashboard auto-refreshes every 30 seconds. Data is also available for download as CSV using the export buttons on the dashboard.

```bash
python3 web_app.py
```

Navigate to `http://127.0.0.1:8050` in your browser. The default Python Dash port is `8050`.

### Country Code Lookup

The dashboard includes an optional country code lookup using the [CleanTalk API](https://cleantalk.org/help/api-ip-info-country-code) to determine the two-digit country code for each IP address.

- Country lookup is **disabled by default** due to performance impact (Pandas dataframe operations).
- Set the `COUNTRY` environment variable to `True` in `public.env` to enable it.
- CleanTalk rate-limits to 1,000 IP lookups per 60 seconds. If rate-limited, set `COUNTRY` back to `False`.

SSH_HoneyPot leverages Python Dash for charts, Dash Bootstrap Components for dark-theme styling, and Pandas for data parsing.

---

## Docker

SSH_HoneyPot includes a `Dockerfile` and `docker-compose.yml` for containerized deployment. Docker provides host-based isolation so the honeypot runs independently from your system environment.

**Start all services (SSH honeypot, HTTP honeypot, dashboard):**

```bash
docker compose up --build -d
```

This starts three containers sharing a common log volume:

| Service | Port | Description |
|---|---|---|
| `ssh-honeypot` | `2222` | SSH honeypot |
| `http-honeypot` | `5000` | HTTP WordPress honeypot |
| `dashboard` | `8050` | Analytics dashboard |

> **Note:** To capture real SSH traffic on port 22, edit `docker-compose.yml` and change `"2222:2222"` to `"22:2222"` under the `ssh-honeypot` service.

**Stop all services:**

```bash
docker compose down
```

**View logs from a running container:**

```bash
docker compose logs -f ssh-honeypot
```

---

## VPS Hosting

For real-world data collection, a Virtual Private Server (VPS) is recommended. A VPS provides a safe, isolated environment with internet access without exposing your home network.

Most VPS providers include a virtual firewall. Ensure the following ports are open:

- `Port 80` — HTTP
- `Port 5000` — HTTP honeypot
- `Port 2223` (or whichever port you configure for SSH)
- `Port 8050` — Dashboard

When using Linux-based distributions, also open ports via UFW:

```bash
ufw enable
ufw allow [port]
```

---

## Running in Background With Systemd

To run SSH_HoneyPot in the background, use Systemd (available on most Linux distributions).

A service template is included in the `systemd/` folder of this repository.

**1. Edit the `ExecStart` line in `honeypy.service` to match your configuration:**

```
ExecStart=/usr/bin/python3 /honeypy.py -a 127.0.0.1 -p 22 --ssh
```

**2. Copy the service file into the systemd directory:**

```bash
cp honeypy.service /etc/systemd/system
```

**3. Reload systemd, then enable and start the service:**

```bash
systemctl daemon-reload
systemctl enable honeypy.service
systemctl start honeypy.service
```

---

## Future Features

- [ ] Telnet support
- [x] HTTP support
- [ ] HTTPS support
- [ ] SMTP support
- [ ] RDP support
- [ ] DNS support
- [ ] Custom DNS support
- [x] Docker support for host-based isolation and deployment
- [x] Systemd support for background execution
- [x] Basic overview Dashboard
- [x] Dynamic Dashboard updates
- [ ] Dashboard hosted independently from the honeypot host
- [x] SSH Banner Tarpit (`-t / --tarpit`)

---

## Helpful Resources

- [How to Build an SSH Honeypot in Python and Docker](https://securehoney.net/blog/how-to-build-an-ssh-honeypot-in-python-and-docker-part-1.html)
- [Deceptive Defense: Building a Python Honeypot](https://medium.com/@abdulsamie488/deceptive-defense-building-a-python-honeypot-to-thwart-cyber-attackers-2a9d2ced2760)
- [SSH Honeypot Gist (cschwede)](https://gist.github.com/cschwede/3e2c025408ab4af531651098331cce45)
- [How to Change the SSH Port on VPS](https://www.hostinger.com/tutorials/how-to-change-ssh-port-vps)
