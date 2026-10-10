"""用**已验证的槽**（5 / 6）把 FLAC 解码到 PCM 试出来——mp3 做对照。

## 已经标定的事实（本会话逐个验证过，方法写在下面）

  * **slot 5 [4 参]** `GetNativeMediaType(stream, typeIndex)` —— 判据：返回的对象能读出
    `MF_MT_MAJOR_TYPE == MFMediaType_Audio`。`_dev/probe_mf_ident.py` 扫出来的。
  * **slot 6 [3 参]** `GetCurrentMediaType(stream)` —— 同一套判据，唯一的 3 参命中。
  * `IMFAttributes::GetUINT32` = 7、`SetUINT32` = 21、`SetGUID` = 24、`GetGUID` = 10
    —— 前几个是拿自己建的 media type 写入再读回校验的，可信。

## 还没标定的

`SetCurrentMediaType` 与 `ReadSample`。这两个**不能靠"hr==0"认**（前两轮就是这么错的）。
这一版的判据是**"读了字节才算对"**：

  对一个候选 `(setcur, read)` 组合，只做一件事——把 `read` 的输出按 `IMFSample::GetBuffer`
  读出字节数。**字节数 > 0 才算这个组合成立。** 于是标定与"能不能解码"合成同一次测量，
  不存在"下标对但解码器不给 PCM"和"下标错"混淆的问题。

    python _dev/probe_mf_pcmtry.py --file player/input/song.mp3        （对照组，必须先通）
    python _dev/probe_mf_pcmtry.py --file player/input/song2.flac
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import time
from ctypes import POINTER, byref, c_void_p, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MF_VERSION = 0x00020070
FIRST_AUDIO = 0xFFFFFFFD

G_MAJOR = "48eba18e-f8c9-4687-bf11-0a74c9f96a8f"
G_SUBTYPE = "f7e34c9a-42e8-4714-b74b-cb29d72c35e5"
G_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"
G_RATE = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
G_BITS = "f2deb57f-40fa-4764-aa33-ed4f2d1ff669"
G_BLOCK = "322de230-f9eb-43bd-ab7a-ff412251541d"
G_BPS = "1aab75c8-cfef-451c-ab95-ac034b8e1731"
AUDIO_MAJOR = "73647561-0000-0010-8000-00aa00389b71"
PCM_SUBTYPE = "00000001-0000-0010-8000-00aa00389b71"

#: 已标定
R_GET_NATIVE = (5, 4)
R_GET_CUR = (6, 3)
#: 候选（要靠"读出字节"来定）
SETCUR_CANDIDATES = (7, 8, 9, 6)
READ_CANDIDATES = (12, 13, 14, 11, 10, 9, 8, 15, 16)
S_GET_BUFFER = 3

HRESULT = ctypes.c_long
_PVP = POINTER(c_void_p)
_PU32 = POINTER(ctypes.c_uint32)
_PI64 = POINTER(ctypes.c_int64)


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s: str = "00000000-0000-0000-0000-000000000000") -> None:  # type: ignore
        super().__init__()
        p = s.strip("{}").split("-")
        self.Data1 = int(p[0], 16)
        self.Data2 = int(p[1], 16)
        self.Data3 = int(p[2], 16)
        rest = p[3] + p[4]
        for i in range(8):
            self.Data4[i] = int(rest[i * 2:i * 2 + 2], 16)

    def __repr__(self) -> str:
        d = bytes(self.Data4)
        return (f"{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-"
                f"{d[0]:02x}{d[1]:02x}-{''.join(f'{b:02x}' for b in d[2:])}")


_GET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), _PU32)
_GET_GUID = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_SET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), ctypes.c_uint32)
_SET_GUID = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
_C3 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, _PVP)
_C4 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PVP)
_SC = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)
_READ = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                           _PU32, _PU32, _PI64, _PVP)
_SB = ctypes.WINFUNCTYPE(HRESULT, c_void_p, _PVP, _PU32, _PU32)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def au32(o, g):
    out = ctypes.c_uint32(0)
    return out.value if _GET_U32(vt(o)[7])(o, byref(GUID(g)), byref(out)) == 0 else None


def aguid(o, g):
    out = GUID()
    return out if _GET_GUID(vt(o)[10])(o, byref(GUID(g)), byref(out)) == 0 else None


def build_pcm(rate, ch, bits=16):
    mt = c_void_p()
    if ctypes.windll.mfplat.MFCreateMediaType(byref(mt)) != 0:
        raise OSError("MFCreateMediaType")
    block = ch * bits // 8
    def sg(g, v):
        gg = GUID(v)
        _SET_GUID(vt(mt)[24])(mt, byref(GUID(g)), byref(gg))
    def su(g, v):
        _SET_U32(vt(mt)[21])(mt, byref(GUID(g)), v)
    sg(G_MAJOR, AUDIO_MAJOR)
    sg(G_SUBTYPE, PCM_SUBTYPE)
    su(G_CHANNELS, ch)
    su(G_RATE, rate)
    su(G_BITS, bits)
    su(G_BLOCK, block)
    su(G_BPS, rate * block)
    return mt


def read_bytes(reader, read_slot, want_frames, block):
    """用候选 read 槽读样本；返回 (字节数, 样本对象数, 首个时间戳)。"""
    actual = ctypes.c_uint32()
    flags = ctypes.c_uint32()
    ts = ctypes.c_int64()
    samp = c_void_p()
    read = _READ(vt(reader)[read_slot])
    total = 0
    got = 0
    frames = 0
    ts0 = None
    while got < want_frames:
        hr = read(reader, FIRST_AUDIO, 0, byref(actual), byref(flags), byref(ts), byref(samp))
        if hr != 0:
            break
        if flags.value & 2:                     # ENDOFSTREAM
            if samp.value:
                rel(samp)
            break
        if samp.value:
            buf = c_void_p()
            mx = ctypes.c_uint32()
            ln = ctypes.c_uint32()
            if _SB(vt(samp)[S_GET_BUFFER])(samp, byref(buf), byref(mx), byref(ln)) == 0:
                total += ln.value
                got += ln.value // max(1, block)
                if ts0 is None:
                    ts0 = ts.value
            rel(samp)
        frames += 1
        if frames > 2000:
            break
    return total, frames, ts0


def try_pair(path: Path, sc: int, rd: int, seconds: float) -> int:
    """在一个 (setcur, read) 组合上试读 PCM。打印一行结果，返回退出码。"""
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    mf.MFStartup(MF_VERSION, 0)
    reader = c_void_p()
    if rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader)) != 0:
        raise SystemExit("open failed")
    nt = c_void_p()
    _C4(vt(reader)[5])(reader, FIRST_AUDIO, 0, byref(nt))
    rate = au32(nt, G_RATE) or 44100
    ch = au32(nt, G_CHANNELS) or 2
    rel(nt)
    block = ch * 2
    mt = build_pcm(rate, ch)
    hr = _SC(vt(reader)[sc])(reader, FIRST_AUDIO, mt)
    rel(mt)
    if hr != 0:
        rel(reader)
        mf.MFShutdown()
        raise SystemExit(1)
    total, frames, ts0 = read_bytes(reader, rd, int(seconds * rate), block)
    rel(reader)
    mf.MFShutdown()
    if total <= 0:
        raise SystemExit(2)
    print(f"PCM {total} bytes / {frames} objects / {total / block / rate:.2f} s "
          f"/ first ts {ts0}")
    raise SystemExit(0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song.mp3"))
    ap.add_argument("--seconds", type=float, default=1.0)
    ap.add_argument("--pair", help="internal: SC,RD")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")

    if a.pair:
        sc, rd = (int(v) for v in a.pair.split(","))
        try_pair(path, sc, rd, a.seconds)
        return

    mf = ctypes.windll.mfplat
    mf.MFStartup(MF_VERSION, 0)
    print(f"file            {path.name}")
    print(f"判据            只有**读出字节**才算这个 (setcur, read) 组合成立。")
    print()
    try:
        import subprocess
        me = Path(__file__).resolve()
        best = None
        for sc in SETCUR_CANDIDATES:
            for rd in READ_CANDIDATES:
                r = subprocess.run(
                    [sys.executable, str(me), "--file", str(path), "--seconds", str(a.seconds),
                     "--pair", f"{sc},{rd}"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
                if r.returncode == 0 and r.stdout.strip():
                    line = r.stdout.strip().splitlines()[-1]
                    print(f"  setcur={sc:2d} read={rd:2d}: {line}")
                    if best is None:
                        best = (sc, rd, line)
                elif r.returncode in (3221225477, -1073741819) or r.returncode < 0:
                    print(f"  setcur={sc:2d} read={rd:2d}: 越界")
                else:
                    print(f"  setcur={sc:2d} read={rd:2d}: exit {r.returncode}")
        print()
        if best:
            print(f"可用组合：SetCurrentMediaType={best[0]}, ReadSample={best[1]}")
            print(f"  {best[2]}")
        else:
            print("没有任何组合读出字节。")
    finally:
        mf.MFShutdown()


if __name__ == "__main__":
    main()

