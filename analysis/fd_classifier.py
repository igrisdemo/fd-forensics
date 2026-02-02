def classify_fd(target, fd_number=None):
    """
    Classify a file descriptor using Linux OS semantics.

    Rules:
    - File descriptors 0, 1, 2 are ALWAYS Standard (stdin, stdout, stderr),
      regardless of what kernel object they point to.
    - Classification is otherwise based on the kernel object type.
    """

    # -----------------------------
    # STANDARD FILE DESCRIPTORS
    # -----------------------------
    if fd_number in (0, 1, 2):
        return "Standard"

    # -----------------------------
    # KERNEL-MANAGED RESOURCES
    # -----------------------------
    if target.startswith("socket:"):
        return "Socket"

    if target.startswith("pipe:"):
        return "Pipe"

    # -----------------------------
    # REGULAR FILES
    # -----------------------------
    if target.startswith("/"):
        return "File"

    # -----------------------------
    # OTHER / UNKNOWN
    # -----------------------------
    return "Other"
