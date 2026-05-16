"""Run Flask + Cloudflare tunnel. Mode: 'fixed' (cszxagent.asia) or 'quick' (trycloudflare)."""
import subprocess, os, time, sys, re, datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

def log(msg):
    with open(os.path.join(PROJECT_DIR, 'bg_debug.log'), 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")

log(f"Starting background_server, mode={sys.argv[1] if len(sys.argv) > 1 else 'fixed'}, cwd={os.getcwd()}")
log(f"python_exe={sys.executable}")

mode = sys.argv[1] if len(sys.argv) > 1 else 'fixed'

# Start Flask
try:
    flask = subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    log(f"Flask started, PID={flask.pid}")
except Exception as e:
    log(f"Flask start FAILED: {e}")
    sys.exit(1)

time.sleep(3)

cf_dir = os.path.join(PROJECT_DIR, 'cloudflared_config')
cf_exe = os.path.join(PROJECT_DIR, 'cloudflared.exe')
log(f"cf_exe={cf_exe}, exists={os.path.exists(cf_exe)}")

if mode == 'fixed':
    config_yml = os.path.join(cf_dir, 'config.yml')
    with open(config_yml, 'w', encoding='utf-8') as f:
        f.write(f'''tunnel: b5084c19-7d13-4e01-93a4-043061f2fec5
credentials-file: {os.path.join(cf_dir, 'credentials.json')}
ingress:
  - hostname: cszxagent.asia
    service: http://localhost:5000
  - hostname: www.cszxagent.asia
    service: http://localhost:5000
  - service: http_status:404
''')
    log("config.yml written")
    try:
        cf = subprocess.Popen([
            cf_exe, 'tunnel',
            '--config', config_yml,
            '--origincert', os.path.join(cf_dir, 'cert.pem'),
            'run', 'math-tutor',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(f"cloudflared fixed started, PID={cf.pid}")
    except Exception as e:
        log(f"cloudflared fixed start FAILED: {e}")
        flask.terminate()
        sys.exit(1)
    time.sleep(3)
    with open('public_url.txt', 'w', encoding='utf-8') as f:
        f.write('https://cszxagent.asia')
    log("public_url.txt written (fixed)")

else:
    log_path = os.path.join(PROJECT_DIR, 'cf_log_{}.txt'.format(int(time.time())))
    log(f"log_path={log_path}")
    # Override HOME so cloudflared won't auto-discover named tunnel credentials from ~/.cloudflared
    env = os.environ.copy()
    env['HOME'] = PROJECT_DIR
    try:
        with open(log_path, 'w', encoding='utf-8') as log_file:
            cf = subprocess.Popen(
                [cf_exe, 'tunnel', '--url', 'http://localhost:5000'],
                stdout=log_file, stderr=subprocess.STDOUT, env=env
            )
        log(f"cloudflared quick started, PID={cf.pid}")
    except Exception as e:
        log(f"cloudflared quick start FAILED: {e}")
        flask.terminate()
        sys.exit(1)

    log("Polling for URL...")
    found = False
    for i in range(30):
        time.sleep(1)
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', content)
            if m:
                url = m.group(0)
                log(f"URL found at iteration {i}: {url}")
                with open('public_url.txt', 'w', encoding='utf-8') as f:
                    f.write(url)
                found = True
                break
        except Exception as e:
            log(f"Poll error at {i}: {e}")
    if not found:
        log("URL NOT FOUND after 30 seconds")
        try:
            log(f"Log file size: {os.path.getsize(log_path)}")
        except:
            pass

    # Cleanup old log files
    for fname in os.listdir(PROJECT_DIR):
        if fname.startswith('cf_log_') and fname != os.path.basename(log_path):
            try:
                os.remove(os.path.join(PROJECT_DIR, fname))
            except Exception:
                pass

# Save PIDs
with open('service_pids.txt', 'w', encoding='utf-8') as f:
    f.write('{}\n{}'.format(flask.pid, cf.pid))
log("service_pids.txt written")

cf.wait()
flask.terminate()
log("Process ended")
