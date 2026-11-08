"""Minimal QEMU driver: serial expect + HMP monitor (screendump, sendkey)."""
import os, re, socket, subprocess, sys, threading, time

class VM:
    def __init__(self, args, d, log='serial.log'):
        self.d = d
        for s in ('serial.sock', 'mon.sock'):
            try: os.unlink(f'{d}/{s}')
            except FileNotFoundError: pass
        self.p = subprocess.Popen(['qemu-system-x86_64', *args,
            '-serial', f'unix:{d}/serial.sock,server=on,wait=off',
            '-monitor', f'unix:{d}/mon.sock,server=on,wait=off', '-display', 'none'])
        for _ in range(100):
            if os.path.exists(f'{d}/serial.sock') and os.path.exists(f'{d}/mon.sock'): break
            time.sleep(0.1)
        self.ser = socket.socket(socket.AF_UNIX); self.ser.connect(f'{d}/serial.sock'); self.ser.settimeout(0.5)
        self.mon = socket.socket(socket.AF_UNIX); self.mon.connect(f'{d}/mon.sock'); self.mon.settimeout(0.5)
        self.buf = ''; self.log = open(f'{d}/{log}', 'a'); self.lock = threading.Lock()
        # Drain serial continuously: an unread socket blocks the guest's serial writes.
        threading.Thread(target=self._pump, daemon=True).start()
    def _pump(self):
        while True:
            try: b = self.ser.recv(65536)
            except socket.timeout: continue
            except OSError: return
            if not b: return
            t = b.decode('utf-8', 'replace')
            with self.lock: self.buf += t
            self.log.write(t); self.log.flush()
    def expect(self, pat, timeout=120):
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                m = re.search(pat, self.buf)
                if m:
                    self.buf = self.buf[m.end():]; return m
            if self.p.poll() is not None: raise SystemExit(f'qemu exited waiting for {pat!r}')
            time.sleep(0.2)
        raise SystemExit(f'TIMEOUT waiting for {pat!r}; tail: {self.buf[-1500:]!r}')
    def send(self, s): self.ser.sendall(s.encode())
    def line(self, s): self.send(s + '\r')
    def hmp(self, cmd):
        self.mon.sendall((cmd + '\n').encode()); time.sleep(0.3)
        try: self.mon.recv(65536)
        except socket.timeout: pass
    def shot(self, name): self.hmp(f'screendump {self.d}/{name} -f png'); time.sleep(0.5)
    def keys(self, text):
        m = {' ': 'spc', '\n': 'ret', '-': 'minus', '.': 'dot', '/': 'slash', '_': 'shift-minus', ':': 'shift-semicolon', '=': 'equal', ',': 'comma', '|': 'shift-backslash', '>': 'shift-dot', '&': 'shift-7', ';': 'semicolon', "'": 'apostrophe', '$': 'shift-4', '(': 'shift-9', ')': 'shift-0', '*': 'shift-8'}
        for ch in text:
            k = m.get(ch) or (f'shift-{ch.lower()}' if ch.isupper() else ch)
            self.hmp(f'sendkey {k}')
    def kill(self):
        self.p.terminate(); self.p.wait(10)
