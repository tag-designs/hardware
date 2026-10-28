#!/usr/bin/env python3
"""LX-16A serial bus servo driver (LewanSoul/Hiwonder bus protocol).

Talks to the servo through the BusLinker V3.0 (CH9102 USB-serial, appears as
/dev/ttyACM0 on Linux) at 115200 8N1.

Packet:  0x55 0x55 ID LEN CMD PARAMS... CHK
         LEN = len(PARAMS) + 3,  CHK = ~(ID + LEN + CMD + sum(PARAMS)) & 0xFF
Multi-byte values are little-endian.

Errata in the vendor PDF (corrected here):
  - position range is 0..1000 for 0..240 deg (0.24 deg/count); the PDF says
    "0~100" in the write-command section.
  - SERVO_ANGLE_OFFSET_READ is command 19 with request length 3; the PDF's
    command section says "Command value: 9, Length: 7".

The bus is half duplex.  If the adapter echoes our own transmission back, the
echo is recognised (same bytes as sent) and skipped.

Usage as a CLI:
  python3 lx16a.py status            # dump everything readable
  python3 lx16a.py move 500 1000     # go to position 500 over 1000 ms
  python3 lx16a.py angle 0 1000      # go to 0 deg (= position 500) over 1 s
  python3 lx16a.py unload            # remove torque
"""

import argparse
import struct
import sys
import time

import serial

DEFAULT_PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5CE5121761-if00"
BROADCAST = 0xFE

# Command values
MOVE_TIME_WRITE = 1
MOVE_TIME_READ = 2
MOVE_TIME_WAIT_WRITE = 7
MOVE_TIME_WAIT_READ = 8
MOVE_START = 11
MOVE_STOP = 12
ID_WRITE = 13
ID_READ = 14
ANGLE_OFFSET_ADJUST = 17
ANGLE_OFFSET_WRITE = 18
ANGLE_OFFSET_READ = 19
ANGLE_LIMIT_WRITE = 20
ANGLE_LIMIT_READ = 21
VIN_LIMIT_WRITE = 22
VIN_LIMIT_READ = 23
TEMP_MAX_LIMIT_WRITE = 24
TEMP_MAX_LIMIT_READ = 25
TEMP_READ = 26
VIN_READ = 27
POS_READ = 28
OR_MOTOR_MODE_WRITE = 29
OR_MOTOR_MODE_READ = 30
LOAD_OR_UNLOAD_WRITE = 31
LOAD_OR_UNLOAD_READ = 32
LED_CTRL_WRITE = 33
LED_CTRL_READ = 34
LED_ERROR_WRITE = 35
LED_ERROR_READ = 36

DEG_PER_COUNT = 240.0 / 1000.0
CENTER = 500


class LX16AError(Exception):
    pass


def checksum(body):
    return (~sum(body)) & 0xFF


def build_packet(servo_id, cmd, params=b""):
    body = bytes([servo_id, len(params) + 3, cmd]) + bytes(params)
    return b"\x55\x55" + body + bytes([checksum(body)])


class LX16A:
    def __init__(self, port=DEFAULT_PORT, servo_id=1, timeout=0.1, retries=2):
        self.ser = serial.Serial(port, 115200, timeout=timeout)
        self.id = servo_id
        self.retries = retries

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # --- transport -------------------------------------------------------

    def _send(self, cmd, params=b"", servo_id=None):
        pkt = build_packet(self.id if servo_id is None else servo_id, cmd, params)
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        self.ser.flush()
        return pkt

    def _read_packet(self):
        """Read one well-formed packet; return (id, cmd, params) or None."""
        deadline = time.monotonic() + self.ser.timeout * 3
        hdr = 0
        while hdr < 2:
            b = self.ser.read(1)
            if not b:
                if time.monotonic() > deadline:
                    return None
                continue
            hdr = hdr + 1 if b == b"\x55" else 0
        head = self.ser.read(2)
        if len(head) < 2:
            return None
        sid, length = head
        # Two 0x55 bytes can precede the real header if ID happens to be 0x55.
        rest = self.ser.read(length - 1)
        if len(rest) != length - 1:
            return None
        body = bytes([sid, length]) + rest[:-1]
        if checksum(body) != rest[-1]:
            raise LX16AError(f"bad checksum in {body.hex(' ')} {rest[-1]:02x}")
        return sid, rest[0], rest[1:-1]

    def _query(self, cmd, servo_id=None):
        """Send a read command and return its parameter bytes."""
        for _ in range(self.retries + 1):
            sent = self._send(cmd, servo_id=servo_id)
            while True:
                pkt = self._read_packet()
                if pkt is None:
                    break
                sid, rcmd, params = pkt
                if build_packet(sid, rcmd, params) == sent:
                    continue  # our own echo on the half-duplex line
                if rcmd == cmd:
                    return params
        raise LX16AError(f"no reply to command {cmd} from servo "
                         f"{self.id if servo_id is None else servo_id}")

    # --- motion ----------------------------------------------------------

    def move(self, pos, ms=0):
        """Move to position 0..1000 over ms milliseconds, starting now."""
        self._send(MOVE_TIME_WRITE, struct.pack("<HH", _clamp(pos, 0, 1000),
                                                _clamp(ms, 0, 30000)))

    def move_checked(self, pos, ms=0, tries=3):
        """move(), then read the target back and resend until it matches.

        Writes are never acknowledged, and the servo occasionally drops one
        (seen twice in 150 swings on 2026-10-27, leaving the stand still for a
        second).  Returns the number of sends; raises if none took.
        """
        want = (_clamp(pos, 0, 1000), _clamp(ms, 0, 30000))
        for n in range(1, tries + 1):
            self.move(*want)
            try:
                if self.move_target() == want:
                    return n
            except Exception:
                pass
        raise IOError(f"servo did not accept move to {want} in {tries} tries")

    def move_deg(self, deg, ms=0):
        """Move to an angle in degrees relative to centre (-120..+120)."""
        self.move(round(CENTER + deg / DEG_PER_COUNT), ms)

    def move_prepare(self, pos, ms=0):
        """Stage a move; it runs on move_start() (broadcast to sync servos)."""
        self._send(MOVE_TIME_WAIT_WRITE, struct.pack("<HH", _clamp(pos, 0, 1000),
                                                     _clamp(ms, 0, 30000)))

    def move_start(self, servo_id=None):
        self._send(MOVE_START, servo_id=servo_id)

    def stop(self):
        self._send(MOVE_STOP)

    def motor_mode(self, speed):
        """Continuous rotation at speed -1000..1000."""
        self._send(OR_MOTOR_MODE_WRITE,
                   struct.pack("<BBh", 1, 0, _clamp(speed, -1000, 1000)))

    def servo_mode(self):
        self._send(OR_MOTOR_MODE_WRITE, struct.pack("<BBh", 0, 0, 0))

    def load(self, on=True):
        """on=True: torque on.  on=False: motor unpowered, shaft free."""
        self._send(LOAD_OR_UNLOAD_WRITE, bytes([1 if on else 0]))

    def unload(self):
        self.load(False)

    def wait_until_stopped(self, min_s=0.0, tol=2, settle=3, poll=0.05,
                           timeout=35.0):
        """Block until position stops changing; return the final position.

        min_s: time to wait before checking, normally the commanded move time.
        The servo takes ~0.3 s to start moving, so without it a steady reading
        during that delay looks like "stopped".
        """
        time.sleep(min_s)
        end = time.monotonic() + timeout
        last, still = None, 0
        while time.monotonic() < end:
            p = self.pos()
            still = still + 1 if last is not None and abs(p - last) <= tol else 0
            if still >= settle:
                return p
            last = p
            time.sleep(poll)
        raise LX16AError("servo did not settle")

    # --- state readback --------------------------------------------------

    def pos(self):
        """Current position in counts (signed; can read slightly < 0)."""
        return struct.unpack("<h", self._query(POS_READ))[0]

    def pos_deg(self):
        return (self.pos() - CENTER) * DEG_PER_COUNT

    def vin(self):
        """Supply voltage in volts."""
        return struct.unpack("<H", self._query(VIN_READ))[0] / 1000.0

    def temp(self):
        """Internal temperature in deg C."""
        return self._query(TEMP_READ)[0]

    def move_target(self):
        """(position, ms) of the last MOVE_TIME_WRITE."""
        return struct.unpack("<HH", self._query(MOVE_TIME_READ))

    def move_wait_target(self):
        return struct.unpack("<HH", self._query(MOVE_TIME_WAIT_READ))

    def mode(self):
        """('servo'|'motor', speed)."""
        m, _, speed = struct.unpack("<BBh", self._query(OR_MOTOR_MODE_READ))
        return ("motor" if m else "servo"), speed

    def loaded(self):
        return bool(self._query(LOAD_OR_UNLOAD_READ)[0])

    def read_id(self):
        """ID of the (single) servo on the bus, via broadcast."""
        return self._query(ID_READ, servo_id=BROADCAST)[0]

    def angle_offset(self):
        """Trim in counts, -125..125 (about +-30 deg)."""
        return struct.unpack("<b", self._query(ANGLE_OFFSET_READ))[0]

    def angle_limits(self):
        return struct.unpack("<HH", self._query(ANGLE_LIMIT_READ))

    def vin_limits(self):
        """(min, max) supply in volts."""
        lo, hi = struct.unpack("<HH", self._query(VIN_LIMIT_READ))
        return lo / 1000.0, hi / 1000.0

    def temp_limit(self):
        return self._query(TEMP_MAX_LIMIT_READ)[0]

    def led_off(self):
        return bool(self._query(LED_CTRL_READ)[0])

    def led_error_mask(self):
        """Bit 0 over-temp, bit 1 over-voltage, bit 2 stalled."""
        return self._query(LED_ERROR_READ)[0]

    def status(self):
        mode, speed = self.mode()
        target, ms = self.move_target()
        return {
            "id": self.id,
            "pos": self.pos(),
            "pos_deg": round(self.pos_deg(), 2),
            "target": target,
            "target_ms": ms,
            "vin_V": self.vin(),
            "temp_C": self.temp(),
            "mode": mode,
            "motor_speed": speed,
            "loaded": self.loaded(),
            "angle_offset": self.angle_offset(),
            "angle_limits": self.angle_limits(),
            "vin_limits_V": self.vin_limits(),
            "temp_limit_C": self.temp_limit(),
            "led_off": self.led_off(),
            "led_error_mask": self.led_error_mask(),
        }

    # --- persistent configuration (written to servo flash) ----------------

    def set_id(self, new_id):
        self._send(ID_WRITE, bytes([_clamp(new_id, 0, 253)]))
        self.id = new_id

    def adjust_offset(self, counts):
        """Apply trim immediately (not saved; call save_offset())."""
        self._send(ANGLE_OFFSET_ADJUST, struct.pack("<b", _clamp(counts, -125, 125)))

    def save_offset(self):
        self._send(ANGLE_OFFSET_WRITE)

    def set_angle_limits(self, lo, hi):
        self._send(ANGLE_LIMIT_WRITE, struct.pack("<HH", _clamp(lo, 0, 1000),
                                                  _clamp(hi, 0, 1000)))

    def set_vin_limits(self, lo_v, hi_v):
        self._send(VIN_LIMIT_WRITE, struct.pack("<HH", round(lo_v * 1000),
                                                round(hi_v * 1000)))

    def set_temp_limit(self, c):
        self._send(TEMP_MAX_LIMIT_WRITE, bytes([_clamp(c, 50, 100)]))

    def set_led_off(self, off):
        self._send(LED_CTRL_WRITE, bytes([1 if off else 0]))

    def set_led_error_mask(self, mask):
        self._send(LED_ERROR_WRITE, bytes([mask & 7]))


def _clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("--id", type=int, default=1)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("id", help="read ID by broadcast (one servo on bus)")
    p = sub.add_parser("move"); p.add_argument("pos", type=int); p.add_argument("ms", type=int, nargs="?", default=1000)
    p = sub.add_parser("angle"); p.add_argument("deg", type=float); p.add_argument("ms", type=int, nargs="?", default=1000)
    sub.add_parser("load")
    sub.add_parser("unload")
    sub.add_parser("stop")
    p = sub.add_parser("watch", help="print position/vin/temp until ^C"); p.add_argument("--hz", type=float, default=10)
    a = ap.parse_args()

    with LX16A(a.port, a.id) as s:
        if a.cmd == "status":
            for k, v in s.status().items():
                print(f"{k:15s} {v}")
        elif a.cmd == "id":
            print(s.read_id())
        elif a.cmd in ("move", "angle"):
            s.move(a.pos, a.ms) if a.cmd == "move" else s.move_deg(a.deg, a.ms)
            p = s.wait_until_stopped(min_s=a.ms / 1000, timeout=5)
            print(f"settled at {p} ({(p - CENTER) * DEG_PER_COUNT:+.2f} deg)")
        elif a.cmd == "load":
            s.load()
        elif a.cmd == "unload":
            s.unload()
        elif a.cmd == "stop":
            s.stop()
        elif a.cmd == "watch":
            t0 = time.monotonic()
            try:
                while True:
                    print(f"{time.monotonic() - t0:8.3f}  pos {s.pos():5d}  "
                          f"vin {s.vin():5.2f} V  temp {s.temp():3d} C", flush=True)
                    time.sleep(1 / a.hz)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    sys.exit(main())
