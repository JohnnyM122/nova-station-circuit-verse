import subprocess
import os

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

# 1. SCP updated cv_panel/app.py and cv_panel/index.html to /tmp
subprocess.run(["scp", "-i", KEY, "-o", "StrictHostKeyChecking=no", "cv_panel/app.py", f"{HOST}:/tmp/app.py"], check=True)
subprocess.run(["scp", "-i", KEY, "-o", "StrictHostKeyChecking=no", "cv_panel/index.html", f"{HOST}:/tmp/index.html"], check=True)

# 2. Remote Python update script
REMOTE_SCRIPT = """
import os

# Update /opt/cv-panel files
os.system("sudo cp /opt/cv-panel/app.py /opt/cv-panel/app.py.bak_sso")
os.system("sudo mv /tmp/app.py /opt/cv-panel/app.py")
os.system("sudo cp /opt/cv-panel/index.html /opt/cv-panel/index.html.bak_sso")
os.system("sudo mv /tmp/index.html /opt/cv-panel/index.html")
os.system("sudo chown pz:pz /opt/cv-panel/app.py /opt/cv-panel/index.html")

# Update /opt/zomboid-panel/client/dist/index.html
zcp_index_path = "/opt/zomboid-panel/client/dist/index.html"
with open(zcp_index_path, "r", encoding="utf-8") as f:
    html = f.read()

sso_script = '''
    <script>
      (function() {
        try {
          function doLogin(user, pass) {
            fetch('/api/auth/login', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              credentials: 'include',
              body: JSON.stringify({username: user, password: pass, rememberMe: true})
            }).then(function(r) {
              if (r.ok) {
                window.location.reload();
              }
            }).catch(function(err){ console.error('ZCP SSO login error:', err); });
          }

          // 1. PostMessage handler from Command Center
          window.addEventListener('message', function(ev) {
            if (ev.origin !== 'https://panel.circuitverse.online' && ev.origin !== 'https://circuitverse.online') return;
            if (ev.data && ev.data.type === 'CV_ZCP_LOGIN' && ev.data.username && ev.data.password) {
              doLogin(ev.data.username, ev.data.password);
            }
          });

          // 2. URL parameter handler (?autouser=...&autopass=...)
          var p = new URLSearchParams(window.location.search);
          var u = p.get('autouser');
          var pwd = p.get('autopass');
          if (u && pwd) {
            window.history.replaceState(null, '', window.location.pathname);
            doLogin(u, pwd);
          }
        } catch(e) { console.error('SSO script init error:', e); }
      })();
    </script>
'''

if "doLogin(user, pass)" not in html:
    os.system(f"sudo cp {zcp_index_path} {zcp_index_path}.bak_sso")
    # Insert right before </head>
    new_html = html.replace("</head>", sso_script + "\\n  </head>")
    with open("/tmp/zcp_index.html", "w", encoding="utf-8") as f:
        f.write(new_html)
    os.system(f"sudo mv /tmp/zcp_index.html {zcp_index_path}")
    os.system(f"sudo chown pz:pz {zcp_index_path}")
    print("Updated ZCP index.html with SSO listener!")
else:
    print("SSO listener already present in ZCP index.html")

# Restart cv-panel
os.system("sudo systemctl restart cv-panel.service")
print("Restarted cv-panel.service!")
"""

cmd = ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, "python3 -"]
res = subprocess.run(cmd, input=REMOTE_SCRIPT.encode("utf-8"), capture_output=True)
print(res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:", res.stderr.decode("utf-8", errors="replace"))
