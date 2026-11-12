import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

# Let's inspect Javacord jar or run a 3-line java test with projectzomboid.jar
cmd = """sudo java -cp /home/pz/pz-server/java/projectzomboid.jar:/home/pz/pz-server/java/. -e '
public class Test {
    public static void main(String[] args) {
        System.out.println("Java OK");
    }
}
' 2>&1 || true"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
