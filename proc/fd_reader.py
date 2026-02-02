import os

def read_fds(pid):
    entries = []
    path = f"/proc/{pid}/fd"

    try:
        for fd in os.listdir(path):
            target = os.readlink(f"{path}/{fd}")
            entries.append({
                "fd": int(fd),
                "target": target
            })
    except Exception:
        pass

    return entries
