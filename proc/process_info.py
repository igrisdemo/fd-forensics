def get_fd_limits(pid):
    soft = hard = "N/A"

    try:
        with open(f"/proc/{pid}/limits") as f:
            for line in f:
                if "Max open files" in line:
                    parts = line.split()
                    soft = parts[3]
                    hard = parts[4]
    except Exception:
        pass

    return soft, hard
