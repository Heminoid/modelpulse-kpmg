import subprocess
import os

script_path = os.path.join(os.getcwd(), "app", "scripts", "generate_pdf.js")
temp_html_path = os.path.join(os.getcwd(), "app", "scripts", "test.html")
out_path = os.path.join(os.getcwd(), "app", "scripts", "out.pdf")

try:
    env = os.environ.copy()
    env["NVM_DIR"] = os.path.expanduser("~/.nvm")
    cmd = f'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh" && node {script_path} {temp_html_path} {out_path}'
    subprocess.run(cmd, shell=True, check=True, capture_output=True, env=env)
    print("Success")
except subprocess.CalledProcessError as e:
    print(f"Failed: {e.stderr.decode()}")
