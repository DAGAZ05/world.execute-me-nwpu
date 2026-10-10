"""Decode a FLAC file far enough to answer questions the player cares about.

Not a general decoder and not meant to ship: it exists to (a) prove a master decodes
bit-exactly (md5 vs STREAMINFO) and (b) hand numpy segments to the analysis below.

    python _dev/flac_probe.py info  input/song2.flac
    python _dev/flac_probe.py md5   input/song2.flac [--limit-seconds N]
    python _dev/flac_probe.py seg   input/song2.flac --at 60 --seconds 30
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

SR_TABLE = [0, 88200, 176400, 192000, 8000, 16000, 22050, 24000, 32000, 44100, 48000, 96000, 0, 0, 0, 0]
BPS_TABLE = [0, 8, 12, 0, 16, 20, 24, 32]


class Bits:
    """MSB-first bit reader over a bytes buffer."""

    __slots__ = ("d", "pos")

    def __init__(self, data: bytes) -> None:
        self.d = data
        self.pos = 0

    def read(self, k: int) -> int:
        if k == 0:
            return 0
        v = 0
        d, pos = self.d, self.pos
        while k > 0:
            byte = d[pos >> 3]
            avail = 8 - (pos & 7)
            take = avail if avail < k else k
            v = (v << take) | ((byte >> (avail - take)) & ((1 << take) - 1))
            pos += take
            k -= take
        self.pos = pos
        return v

    def unary(self) -> int:
        z = 0
        d, pos = self.d, self.pos
        while True:
            byte = d[pos >> 3]
            avail = 8 - (pos & 7)
            chunk = byte & ((1 << avail) - 1)
            if chunk == 0:
                z += avail
                pos += avail
                continue
            lead = avail - chunk.bit_length()
            pos += lead + 1
            self.pos = pos
            return z + lead

    def skip(self, k: int) -> None:
        self.pos += k

    def signed(self, k: int) -> int:
        v = self.read(k)
        return v - (1 << k) if k and v >= (1 << (k - 1)) else v


def unzigzag(u: int) -> int:
    return (u >> 1) ^ -(u & 1)


def parse_metadata(fh) -> dict:
    magic = fh.read(4)
    if magic != b"fLaC":
        raise SystemExit("not a FLAC file")
    info: dict = {}
    blocks: list[tuple[int, int, str]] = []
    while True:
        head = fh.read(4)
        if len(head) < 4:
            break
        last, btype = head[0] & 0x80, head[0] & 0x7F
        length = int.from_bytes(head[1:4], "big")
        start = fh.tell()
        if btype == 0:
            d = fh.read(length)
            packed = int.from_bytes(d[10:18], "big")
            info.update(
                sample_rate=(packed >> 44) & 0xFFFFF,
                channels=((packed >> 41) & 0x7) + 1,
                bits=((packed >> 36) & 0x1F) + 1,
                total_samples=packed & 0xFFFFFFFFF,
                md5=d[18:34].hex(),
            )
            info["duration_s"] = info["total_samples"] / info["sample_rate"]
        blocks.append((btype, start, length))
        fh.seek(start + length)
        if last:
            break
    info["data_offset"] = fh.tell()
    info["blocks"] = [(t, off, ln) for t, off, ln in blocks]
    return info


def _find_sync(data: bytes, start: int, limit: int) -> int:
    """First offset >= start whose bytes look like a FLAC frame header.

    The sync word alone is not enough - `ff f8`/`ff f9` occurs inside frame data too, which is how a
    naive scanner ends up with 2800 candidates where the stream has 2282 frames. So a candidate must
    also survive the header's own constraints: the reserved bit clear, and the channel assignment and
    bit-depth codes inside the range the format defines.
    """
    pos = start
    while True:
        i = data.find(b"\xff\xf8", pos, limit)
        j = data.find(b"\xff\xf9", pos, limit)
        cands = [x for x in (i, j) if x >= 0]
        if not cands:
            return -1
        i = min(cands)
        if i + 5 > limit:
            return -1
        b2, b3 = data[i + 2], data[i + 3]
        bs_code, sr_code = b2 >> 4, b2 & 0x0F
        ch_code, bps_code = b3 >> 4, (b3 & 0x0E) >> 1
        if (b3 & 0x01) == 0 and bs_code != 0 and sr_code != 15 and ch_code <= 10 and bps_code != 3:
            return i
        pos = i + 2


def _utf8(data: bytes, pos: int) -> tuple[int, int]:
    """Read one FLAC variable-length (UTF-8-style) integer; return (value, bytes_consumed)."""
    b0 = data[pos]
    if b0 < 0x80:
        return b0, 1
    n = 0
    mask = 0x80
    while b0 & mask:
        n += 1
        mask >>= 1
    if n < 2 or n > 7:
        raise ValueError(f"bad UTF-8 lead byte {b0:#04x}")
    v = b0 & ((1 << (7 - n)) - 1)
    for k in range(1, n):
        b = data[pos + k]
        if (b & 0xC0) != 0x80:
            raise ValueError("bad UTF-8 continuation")
        v = (v << 6) | (b & 0x3F)
    return v, n


def _decode_subframe(br: Bits, bs: int, bps: int) -> np.ndarray:
    br.skip(1)                      # zero pad
    sf_type = br.read(6)
    wasted = 0
    if br.read(1):
        wasted = br.unary() + 1
    eff = bps - wasted
    if sf_type == 0:                # constant
        s = np.full(bs, br.signed(eff), dtype=np.int64)
    elif sf_type == 1:              # verbatim
        s = np.frombuffer(
            bytes(br.read(8) for _ in range(eff // 8)) if eff % 8 == 0 else b"",
            dtype=">i2" if eff == 16 else None,
        ) if False else np.array([br.signed(eff) for _ in range(bs)], dtype=np.int64)
    else:                           # LPC
        order = sf_type - 1
        shift = br.unary()
        if br.read(1):
            shift = -br.unary()
        coeffs = np.array([br.signed(eff) for _ in range(order)], dtype=np.int64)
        method = br.read(2)
        pbits = 4 if method == 0 else 5
        escape = (1 << pbits) - 1
        parts = 1 << (4 if method == 0 else 5)
        shiftbits = 12 if method == 0 else 13
        resid = np.zeros(bs, dtype=np.int64)
        for p0 in range(0, bs, 4096):
            nb = min(4096, bs - p0)
            params = [br.read(pbits) for _ in range(parts)]
            for j in range(nb):
                p = params[j >> shiftbits]
                if p == escape:
                    n2 = br.read(5)
                    resid[p0 + j] = br.signed(n2) if n2 else 0
                else:
                    q = br.unary()
                    r = br.read(p)
                    resid[p0 + j] = unzigzag((q << p) | r)
        s = np.zeros(bs, dtype=np.int64)
        if order:
            for j in range(bs):
                lo = j - order
                if lo < 0:
                    acc = 0
                    for t in range(order):
                        idx = j - 1 - t
                        if idx >= 0:
                            acc += int(coeffs[t]) * int(s[idx])
                else:
                    acc = int(np.dot(coeffs, s[j - order:j][::-1]))
                s[j] = (resid[j] + acc) >> shift
        else:
            s = resid
    if wasted:
        s = s << wasted
    return s


def iter_frames(path: Path, stop_after_samples: int | None = None):
    """Yield (frame_index, block_size, channels_list, first_sample_index, info, channel_code).

    Header parsing follows libFLAC's `read_frame_header_` field by field; the frame/sample number is
    a byte-aligned UTF-8-style integer, NOT a bit-read one, which is the mistake that made an earlier
    version of this file read a nonsense channel assignment and then die on frame 1.
    """
    info = parse_metadata(path.open("rb"))
    with path.open("rb") as fh:
        fh.seek(info["data_offset"])
        data = fh.read()
    n = len(data)
    pos = 0
    idx = 0
    done = 0
    nch_stream = info["channels"]
    while pos < n - 2:
        i = _find_sync(data, pos, n)
        if i < 0:
            break
        b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
        variable = bool(b1 & 1)
        bs_code, sr_code = b2 >> 4, b2 & 0x0F
        ch_code, bps_code = b3 >> 4, (b3 & 0x0E) >> 1
        p = i + 4
        try:
            _number, ln = _utf8(data, p)
            p += ln
        except Exception:
            pos = i + 2
            continue
        if bs_code == 6:
            bs = data[p] + 1
            p += 1
        elif bs_code == 7:
            bs = int.from_bytes(data[p:p + 2], "big") + 1
            p += 2
        elif bs_code == 0:
            bs = nch_stream and 0  # unparseable without STREAMINFO min/max blocksize
            bs = 0
        elif bs_code == 1:
            bs = 192
        elif 2 <= bs_code <= 5:
            bs = 576 << (bs_code - 2)
        else:
            bs = 256 << (bs_code - 8)
        if sr_code == 12:
            p += 1
        elif sr_code in (13, 14):
            p += 2
        p += 1                                  # header CRC-8
        nch = 2 if ch_code >= 8 else ch_code + 1
        if ch_code > 10:
            nch = nch_stream
        bps = info["bits"] if bps_code == 0 else BPS_TABLE[bps_code]
        if not bs:
            pos = i + 2
            continue
        br = Bits(data[i:n])
        br.pos = p * 8
        chans = []
        ok = True
        for _ in range(nch):
            try:
                chans.append(_decode_subframe(br, bs, bps))
            except Exception:
                ok = False
                break
        if not ok:
            pos = i + 2
            continue
        yield idx, bs, chans, done, info, ch_code
        done += bs
        idx += 1
        if stop_after_samples is not None and done >= stop_after_samples:
            return
        pos = (br.pos + 7) // 8 + 2             # skip frame CRC-16 (and any padding)


def decorrelate(chans: list[np.ndarray], ch_code: int) -> list[np.ndarray]:
    """Undo the stereo decorrelation the frame's channel assignment asked for."""
    if ch_code == 8:      # left/side
        l, s = chans
        return [l, l - s]
    if ch_code == 9:      # right/side
        s, r = chans
        return [s + r, r]
    if ch_code == 10:     # mid/side
        m, s = chans
        m = (m << 1) | (s & 1)
        return [(m + s) >> 1, (m - s) >> 1]
    return chans


def cmd_info(path: Path) -> None:
    info = parse_metadata(path.open("rb"))
    print(f"file         {path}  ({path.stat().st_size / 1e6:.1f} MB)")
    print(f"sample rate  {info['sample_rate']} Hz")
    print(f"bits/channel {info['bits']}")
    print(f"channels     {info['channels']}")
    print(f"total        {info['total_samples']} samples = {info['duration_s']:.6f} s")
    print(f"pcm md5      {info['md5']}")
    for btype, off, ln in info["blocks"]:
        names = {0: "STREAMINFO", 1: "PADDING", 2: "APPLICATION", 3: "SEEKTABLE",
                 4: "VORBIS_COMMENT", 5: "CUESHEET", 6: "PICTURE"}
        print(f"  block type {btype} ({names.get(btype, '?')})  offset {off}  {ln} bytes")


def cmd_md5(path: Path, limit_seconds: float | None) -> None:
    """Decode and hash the PCM; compare with STREAMINFO's md5."""
    info = parse_metadata(path.open("rb"))
    stop = None if limit_seconds is None else int(limit_seconds * info["sample_rate"])
    h = hashlib.md5()
    t0 = time.perf_counter()
    total = 0
    interleave = np.empty(0, dtype="<i2") if info["bits"] <= 16 else None
    for idx, bs, chans, done, _info, ch_code in iter_frames(path, stop):
        block = np.stack(decorrelate(chans, ch_code), axis=1).astype(np.int32)
        if info["bits"] == 16:
            raw = block.astype("<i2").tobytes()
        else:
            raw = b"".join(int(v).to_bytes(3, "little", signed=True) for row in block for v in row)
        h.update(raw)
        total += bs
    dt = time.perf_counter() - t0
    print(f"decoded      {total} samples ({total / info['sample_rate']:.3f} s) in {dt:.1f} s"
          f"  = {total / max(dt, 1e-9) / 1000:.0f} ksamples/s")
    print(f"pcm md5      {h.hexdigest()}")
    print(f"streaminfo   {info['md5']}")
    if limit_seconds is None:
        print("VERDICT      " + ("BIT-EXACT MATCH" if h.hexdigest() == info["md5"] else "MISMATCH"))
    else:
        print("(partial decode: md5 comparison not applicable)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["info", "md5", "seg"])
    ap.add_argument("path", type=Path)
    ap.add_argument("--limit-seconds", type=float, default=None)
    ap.add_argument("--at", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, default=10.0)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.cmd == "info":
        cmd_info(args.path)
    elif args.cmd == "md5":
        cmd_md5(args.path, args.limit_seconds)
    else:
        info = parse_metadata(args.path.open("rb"))
        sr = info["sample_rate"]
        want0 = int(args.at * sr)
        want1 = int((args.at + args.seconds) * sr)
        acc = []
        for idx, bs, chans, done, _info, ch_code in iter_frames(args.path):
            if done + bs < want0:
                continue
            if done > want1:
                break
            block = np.stack(decorrelate(chans, ch_code), axis=1).astype(np.float64)
            a = max(0, want0 - done)
            b = min(bs, want1 - done)
            acc.append(block[a:b])
        seg = np.concatenate(acc) if acc else np.zeros((0, info["channels"]))
        out = Path("_dev") / (args.path.stem + "_seg.npy")
        np.save(out, seg.astype(np.float32))
        print(f"saved {seg.shape} -> {out}")


if __name__ == "__main__":
    main()
