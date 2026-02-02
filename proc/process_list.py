import os
import pwd

def list_processes():
    processes = []

    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue

        try:
            with open(f"/proc/{pid}/comm") as f:
                name = f.read().strip()

            with open(f"/proc/{pid}/status") as f:
                status = f.read()

            uid_line = next(l for l in status.splitlines() if l.startswith("Uid:"))
            uid = int(uid_line.split()[1])
            user = pwd.getpwuid(uid).pw_name

            fd_count = len(os.listdir(f"/proc/{pid}/fd"))

            processes.append({
                "pid": int(pid),
                "name": name,
                "user": user,
                "fd_count": fd_count
            })

        except Exception:
            continue

    return sorted(processes, key=lambda x: x["fd_count"], reverse=True)
