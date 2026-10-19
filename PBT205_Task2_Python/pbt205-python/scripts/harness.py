"""Tiny test harness: start the real programs as child processes, wait for output,
and save a transcript to docs/test-evidence/ (used by test_trading.py)."""
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = os.environ.get("RABBIT_ENDPOINT", "5672")


class Proc:
    def __init__(self, label, popen):
        self.label = label
        self.popen = popen
        self.lines = []

    @property
    def exited(self):
        return self.popen.poll()


class Session:
    def __init__(self, title):
        self.title = title
        self.procs = []
        self.checks = []
        self._lock = threading.Lock()
        stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        self.log = [f"# {title}", f"# Run at {stamp}  endpoint={ENDPOINT}", "# Broker: RabbitMQ", ""]

    def log_line(self, text):
        with self._lock:
            self.log.append(text)

    def start(self, label, script, args=()):
        """Run `python -u <script> <args>`; every output line is stamped with the label."""
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        popen = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / script), *map(str, args)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=env,
        )
        proc = Proc(label, popen)
        self.log_line(f"$ {label}: python {script} {' '.join(map(str, args))}")

        def reader():
            for line in popen.stdout:
                line = line.rstrip("\r\n")
                if line:
                    proc.lines.append(line)
                    self.log_line(f"[{label}] {line}")

        threading.Thread(target=reader, daemon=True).start()
        self.procs.append(proc)
        return proc

    def wait_for(self, proc, pattern, seconds=8):
        regex = re.compile(pattern)
        end = time.time() + seconds
        while time.time() < end:
            if any(regex.search(line) for line in proc.lines):
                return True
            time.sleep(0.05)
        return False

    def wait_exit(self, proc, seconds=8):
        try:
            code = proc.popen.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return None
        time.sleep(0.2)          # let the reader thread collect the last lines
        return code

    def has(self, proc, pattern):
        regex = re.compile(pattern)
        return any(regex.search(line) for line in proc.lines)

    def check(self, name, ok):
        ok = bool(ok)
        self.checks.append((name, ok))
        self.log_line(f"{'PASS' if ok else 'FAIL'} - {name}")
        print(f"{'PASS' if ok else 'FAIL'} - {name}", flush=True)

    def finish(self, filename):
        for proc in self.procs:
            if proc.exited is None:
                proc.popen.terminate()
        time.sleep(0.3)
        failed = sum(1 for _, ok in self.checks if not ok)
        self.log_line("")
        self.log_line(f"RESULT: {len(self.checks) - failed}/{len(self.checks)} checks passed")
        out = ROOT / "docs" / "test-evidence" / filename
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(self.log) + "\n", encoding="utf-8")
        print(f"Transcript saved: docs/test-evidence/{filename}", flush=True)
        sys.exit(1 if failed else 0)


def sleep(seconds):
    time.sleep(seconds)
