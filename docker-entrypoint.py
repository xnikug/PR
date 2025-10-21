import configparser
import subprocess
import sys

# Read configuration
config = configparser.ConfigParser()
config.read('/app/server.conf')

# Get configuration values
host = config.get('server', 'host', fallback='0.0.0.0')
port = config.get('server', 'port', fallback='8080')
doc_root = config.get('server', 'document_root', fallback='/app/public')
use_threads = config.getboolean('server', 'use_threads', fallback=True)
simulate_delay = config.getboolean('server', 'simulate_delay', fallback=False)
enable_rate_limiting = config.getboolean('server', 'enable_rate_limiting', fallback=True)
use_unsafe_counter = config.getboolean('server', 'use_unsafe_counter', fallback=False)

# Build command arguments
args = ['python3', 'server.py', doc_root, port]

if not use_threads:
    args.append('--single-threaded')
if simulate_delay:
    args.append('--delay')
if not enable_rate_limiting:
    args.append('--no-rate-limit')
if use_unsafe_counter:
    args.append('--unsafe-counter')

# Execute server
subprocess.run(args)
