
from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _find_free_port(preferred: int, fallback_start: int = 10000, fallback_end: int = 11000) -> int:
    if not _is_port_open("127.0.0.1", preferred):
        return preferred
    for p in range(fallback_start, fallback_end):
        if not _is_port_open("127.0.0.1", p):
            return p
    return preferred


def _tor_executable_candidates() -> list[str]:
    candidates = []
    # 1) Environment override
    env_tor = os.environ.get("TOR_EXE")
    if env_tor:
        candidates.append(env_tor)

    # 2) Plain 'tor' on PATH
    tor_on_path = shutil.which("tor")
    if tor_on_path:
        candidates.append(tor_on_path)

    # 3) Common Windows Tor Browser locations
    if sys.platform.startswith("win"):
        program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
        common = [
            Path(program_files) / "Tor Browser" / "Browser" / "TorBrowser" / "Tor" / "tor.exe",
            Path(program_files_x86) / "Tor Browser" / "Browser" / "TorBrowser" / "Tor" / "tor.exe",
            Path("C:/Tor/tor.exe"),
        ]
        for p in common:
            if p.exists():
                candidates.append(str(p))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


class TorService:
    def __init__(self, data_dir: Optional[Path] = None):
        self._lock = threading.RLock()
        self.process: Optional[subprocess.Popen] = None
        self.is_running: bool = False
        self._socks_port: Optional[int] = None
        self.data_dir = data_dir or (Path.cwd() / "tor_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_socks_port(self) -> Optional[int]:
        return self._socks_port

    # --- Discovery helpers
    def _use_existing_if_available(self) -> bool:
        """Prefer an already-running Tor instance on common ports."""
        # Try system Tor default first (9050), then Tor Browser (9150)
        for p in (9050, 9150):
            if _is_port_open("127.0.0.1", p):
                self._socks_port = p
                self.is_running = True
                logger.info(f"Using existing Tor SOCKS proxy on port {p}")
                return True
        return False

    def _start_new_process(self) -> bool:
        """Attempt to start a new Tor process if we can find the executable."""
        exe_candidates = _tor_executable_candidates()
        if not exe_candidates:
            logger.warning("Tor executable not found. Set TOR_EXE env var or install Tor.")
            return False

        socks_port = _find_free_port(9050)
        control_port = _find_free_port(9051)

        torrc = self.data_dir / "torrc"
        try:
            torrc.write_text(
                f"SocksPort {socks_port}\n"
                f"ControlPort {control_port}\n"
                f"DataDirectory {self.data_dir.as_posix()}\n"
                f"Log notice stdout\n"
            )
        except Exception:
            # Non-fatal; Tor can run without this file since we pass CLI args
            pass

        tor_exe = exe_candidates[0]
        args = [
            tor_exe,
            f"--SocksPort", str(socks_port),
            f"--ControlPort", str(control_port),
            f"--DataDirectory", str(self.data_dir),
            "--Log", "notice stdout",
        ]

        creationflags = 0
        startupinfo = None
        if sys.platform.startswith("win"):
            # Hide console window on Windows
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.data_dir),
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            # Wait briefly for Tor to open the SOCKS port
            for _ in range(50):  # ~5 seconds total
                if _is_port_open("127.0.0.1", socks_port):
                    self._socks_port = socks_port
                    self.is_running = True
                    logger.info(f"✅ Tor service started on port {socks_port}")
                    return True
                # If the process died early, stop waiting
                if self.process.poll() is not None:
                    break
                time.sleep(0.1)

            logger.error("Tor failed to start within timeout.")
            return False
        except Exception as e:
            logger.error(f"Failed to start Tor: {e}")
            return False

    # --- Public controls
    def start(self) -> bool:
        with self._lock:
            if self.is_running:
                return True
            # Prefer to use an existing Tor instance
            if self._use_existing_if_available():
                return True
            # Try to start a new one
            return self._start_new_process()

    def stop(self) -> None:
        with self._lock:
            try:
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                self.process = None
            except Exception as e:
                logger.warning(f"Error while stopping Tor: {e}")
            finally:
                # Don't mark not running if we're still able to reach an external Tor (user's Tor Browser)
                if self._socks_port and _is_port_open("127.0.0.1", self._socks_port):
                    # External Tor still up; keep running state true
                    self.is_running = True
                else:
                    self.is_running = False
                    self._socks_port = None

    def __del__(self):
        # Best effort cleanup of embedded process only
        if self.process:
            try:
                self.stop()
            except Exception:
                pass


# Singleton instance
_tor_service: Optional[TorService] = None
_singleton_lock = threading.Lock()


def get_tor_service() -> TorService:
    global _tor_service
    if _tor_service is None:
        with _singleton_lock:
            if _tor_service is None:
                data_dir = Path(os.environ.get("TOR_DATA_DIR", Path.cwd() / "tor_data"))
                _tor_service = TorService(data_dir=data_dir)
    return _tor_service


def ensure_tor_running() -> Optional[int]:
    """Ensure a Tor SOCKS proxy is available. Returns the port if available."""
    service = get_tor_service()
    try:
        if service.start() and service.get_socks_port():
            return service.get_socks_port()
    except Exception as e:
        logger.error(f"ensure_tor_running error: {e}")
    return None

