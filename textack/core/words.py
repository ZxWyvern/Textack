# textack/core/words.py
import random

TIER1 = ["ls", "cd", "pwd", "cat", "echo", "clear", "whoami", "mkdir", "touch", "rm"]
TIER2 = ["sudo", "grep", "chmod", "chown", "ps aux", "kill", "tar -xzf", "ssh", "curl", "wget"]
TIER3 = ["sudo apt update", "ps aux | grep nginx", "chmod +x main.py", "systemctl status sshd", "find /etc -name nginx", "tail -f /var/log/syslog", "df -h | grep sda", "ls -la ~/Documents"]
def pick_word(wave: int, rng=random) -> str:
    if wave <= 1:
        pool = TIER1
    elif wave == 2:
        pool = TIER1 + TIER2
    else:
        pool = TIER1 + TIER2 + TIER3
    return rng.choice(pool)
