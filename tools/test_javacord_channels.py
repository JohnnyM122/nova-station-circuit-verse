import subprocess

KEY = r"C:\Users\SysAdmin\.ssh\id_ed25519_tailscale"
HOST = "ubuntu@62.238.81.224"

cmd = """sudo python3 -c '
import json, os

with open("/etc/cv-panel/config.json") as f:
    cfg = json.load(f)

token = cfg["discord_bot_token"]

lines = [
    "import org.javacord.api.DiscordApi;",
    "import org.javacord.api.DiscordApiBuilder;",
    "import org.javacord.api.entity.channel.TextChannel;",
    "",
    "public class TestJavacord {",
    "    public static void main(String[] args) throws Exception {",
    "        System.out.println(\\"Starting Javacord test...\\");",
    "        DiscordApi api = new DiscordApiBuilder()",
    "            .setToken(\\"" + token + "\\")",
    "            .login().join();",
    "        System.out.println(\\"Logged in as: \\" + api.getYourself().getDiscriminatedName());",
    "        for (TextChannel ch : api.getTextChannels()) {",
    "            if (ch.getName().contains(\\"pz\\")) {",
    "                System.out.println(\\"Found text channel: [\\" + ch.getName() + \\"]\\");",
    "            }",
    "        }",
    "        api.disconnect();",
    "        System.out.println(\\"Test complete.\\");",
    "        System.exit(0);",
    "    }",
    "}"
]

with open("/tmp/TestJavacord.java", "w") as f:
    f.write("\\n".join(lines))

os.system("/home/pz/pz-server/jre64/bin/java -cp \\"/home/pz/pz-server/java/projectzomboid.jar:/home/pz/pz-server/java/*\\" /tmp/TestJavacord.java")
'
"""

res = subprocess.run(["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", HOST, cmd], stdin=subprocess.DEVNULL, capture_output=True)
print("OUT:\n", res.stdout.decode("utf-8", errors="replace"))
if res.stderr:
    print("STDERR:\n", res.stderr.decode("utf-8", errors="replace"))
