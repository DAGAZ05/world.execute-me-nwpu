"""把 `IMFSourceReader` 的三个关键槽**标定**出来：`SetCurrentMediaType` / `GetNativeMediaType` / `ReadSample`。

## 为什么下标要靠标定

这个壳子里数错过三轮，所以规则定死：**每个槽都必须用一个"成功判据"证明它是谁**，
而不是数序号、也不是"hr==0 就算"。

  * `SetCurrentMediaType` —— **用原生类型设回去必须成功**。这是最强的判据：
    把原生类型设回它自己，任何实现都必须接受；它不依赖解码器愿不愿意给 PCM。
    （前两轮用"设 PCM 是否成功"当判据，于是把"解码器不给 PCM"误判成"这个槽不是它"。）
  * `GetNativeMediaType` —— 返回的 `IMFMediaType` 里必须能读出非零采样率。
  * `ReadSample` —— 调一次返回 hr==0，且要么给 NULL 样本、要么 `IMFSample::GetBuffer`
    能读出长度 > 0。

## 越界怎么办

Windows 的访问越界是进程级的，`try/except` 拦不住。所以每个槽在**自己的子进程**里试。

    python _dev/probe_mf_calibrate.py --file player/input/song.mp3
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
from ctypes import POINTER, byref, c_void_p, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MF_VERSION = 0x00020070
FIRST_AUDIO = 0xFFFFFFFD
ATTR_GET_U32 = 7
S_GET_BUFFER = 3

G_RATE = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
G_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"

HRESULT = ctypes.c_long
_PVP = POINTER(c_void_p)
_PU32 = POINTER(ctypes.c_uint32)
_PI64 = POINTER(ctypes.c_int64)


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s: str) -> None:  # type: ignore[override]
        super().__init__()
        p = s.strip("{}").split("-")
        self.Data1 = int(p[0], 16)
        self.Data2 = int(p[1], 16)
        self.Data3 = int(p[2], 16)
        rest = p[3] + p[4]
        for i in range(8):
            self.Data4[i] = int(rest[i * 2:i * 2 + 2], 16)


_GET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), _PU32)
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
_SET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)
_GET_NATIVE = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PVP)
_READ = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                           _PU32, _PU32, _PI64, _PVP)
_S_GET_BUFFER = ctypes.WINFUNCTYPE(HRESULT, c_void_p, _PVP, _PU32, _PU32)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def au32(obj, guid: str):
    out = ctypes.c_uint32(0)
    hr = _GET_U32(vt(obj)[ATTR_GET_U32])(obj, byref(GUID(guid)), byref(out))
    return out.value if hr == 0 else None


def _open(path: Path):
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, 0) != 0:
        raise SystemExit("MFStartup failed")
    reader = c_void_p()
    if rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader)) != 0:
        raise SystemExit("open failed")
    return mf, reader


def slot_setcur(path: Path, idx: int) -> None:
    """判据：把**原生**类型设回去必须成功。"""
    mf, reader = _open(path)
    try:
        nt = c_void_p()
        if _GET_NATIVE(vt(reader)[6])(reader, FIRST_AUDIO, 0, byref(nt)) != 0 or not nt.value:
            raise SystemExit(3)
        hr = _SET_CUR(vt(reader)[idx])(reader, FIRST_AUDIO, nt)
        rel(nt)
        if hr != 0:
            raise SystemExit(1)
        print("OK " + json.dumps({"slot": idx}))
    finally:
        rel(reader)
        mf.MFShutdown()


def slot_native(path: Path, idx: int) -> None:
    """判据：返回的类型里能读出非零采样率。"""
    mf, reader = _open(path)
    try:
        out = c_void_p()
        if _GET_NATIVE(vt(reader)[idx])(reader, FIRST_AUDIO, 0, byref(out)) != 0 or not out.value:
            raise SystemExit(1)
        rate = au32(out, G_RATE)
        ch = au32(out, G_CHANNELS)
        rel(out)
        if not rate:
            raise SystemExit(2)
        print("OK " + json.dumps({"slot": idx, "rate": rate, "channels": ch}))
    finally:
        rel(reader)
        mf.MFShutdown()


def slot_read(path: Path, idx: int, setcur: int) -> None:
    """判据：hr==0，且样本要么为 NULL、要么 GetBuffer 给出长度。先设成 PCM 再读。"""
    mf, reader = _open(path)
    try:
        # 设 PCM（用已标定的 setcur）
        nt = c_void_p()
        _GET_NATIVE(vt(reader)[6])(reader, FIRST_AUDIO, 0, byref(nt))
        rate = au32(nt, G_RATE) or 44100
        ch = au32(nt, G_CHANNELS) or 2
        rel(nt)
        mt = build_pcm(rate, ch)
        if _SET_CUR(vt(reader)[setcur])(reader, FIRST_AUDIO, mt) != 0:
            rel(mt)
            raise SystemExit(4)
        rel(mt)
        actual = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        ts = ctypes.c_int64()
        samp = c_void_p()
        hr = _READ(vt(reader)[idx])(reader, FIRST_AUDIO, 0, byref(actual), byref(flags),
                                    byref(ts), byref(samp))
        if hr != 0:
            raise SystemExit(1)
        if not samp.value:
            print("OK " + json.dumps({"slot": idx, "bytes": 0, "note": "null"}))
            return
        buf = c_void_p()
        mx = ctypes.c_uint32()
        ln = ctypes.c_uint32()
        ok = _S_GET_BUFFER(vt(samp)[S_GET_BUFFER])(samp, byref(buf), byref(mx), byref(ln)) == 0
        rel(samp)
        if not ok:
            raise SystemExit(2)
        print("OK " + json.dumps({"slot": idx, "bytes": ln.value}))
    finally:
        rel(reader)
        mf.MFShutdown()


def build_pcm(rate: int, ch: int, bits: int = 16):
    mf = ctypes.windll.mfplat
    mt = c_void_p()
    mf.MFCreateMediaType(byref(mt))
    block = ch * bits // 8
    _SET_G = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
    _SET_U = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), ctypes.c_uint32)
    def sg(g, v):
        gg = GUID(v)
        _SET_G(vt(mt)[24])(mt, byref(GUID(g)), byref(gg))
    def su(g, v):
        _SET_U(vt(mt)[21])(mt, byref(GUID(g)), v)
    sg("48eba18e-f8c9-4687-bf11-0a74c9f96a8f", "73647561-0000-0010-8000-00aa00389b71")
    sg("f7e34c9a-42e8-4714-b74b-cb29d72c35e5", "00000001-0000-0010-8000-00aa00389b71")
    su(G_CHANNELS, ch)
    su(G_RATE, rate)
    su("f2deb57f-40fa-4764-aa33-ed4f2d1ff669", bits)
    su("322de230-f9eb-43bd-ab7a-ff412251541d", block)
    su("1aab75c8-cfef-451c-ab95-ac034b8e1731", rate * block)
    return mt


def spawn(args: list) -> tuple[int, str]:
    me = Path(__file__).resolve()
    r = subprocess.run([sys.executable, str(me)] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song.mp3"))
    ap.add_argument("--mode", choices=["setcur", "native", "read"], help="internal")
    ap.add_argument("--slot", type=int)
    ap.add_argument("--setcur", type=int, default=6)
    a = ap.parse_args()
    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")
    if a.mode:
        {"setcur": slot_setcur, "native": slot_native}[a.mode](path, a.slot) \
            if a.mode != "read" else slot_read(path, a.slot, a.setcur)
        return

    print(f"file   {path.name}")
    print()
    print("标定 SetCurrentMediaType（判据：用原生类型设回去必须成功）")
    setcur = None
    for i in range(3, 14):
        rc, out = spawn(["--mode", "setcur", "--slot", str(i), "--file", str(path)])
        if rc == 0 and out.startswith("OK "):
            print(f"  slot {i:2d}: HIT")
            setcur = i
        else:
            print(f"  slot {i:2d}: --   {'越界' if rc in (3221225477, -1073741819) else f'exit {rc}'}")
    print(f"  -> SetCurrentMediaType = {setcur}" if setcur is not None else "  -> 未命中")
    if setcur is None:
        return

    print()
    print("标定 GetNativeMediaType（判据：能读出非零采样率）")
    for i in range(3, 14):
        rc, out = spawn(["--mode", "native", "--slot", str(i), "--file", str(path)])
        tag = "HIT" if rc == 0 and out.startswith("OK ") else ("越界" if rc in (3221225477, -1073741819) else f"exit {rc}")
        print(f"  slot {i:2d}: {tag}" + (f"  {out[3:]}" if tag == "HIT" else ""))

    print()
    print(f"标定 ReadSample（判据：hr==0 且样本可读；先按已标定的 SetCurrentMediaType={setcur} 设成 PCM）")
    for i in range(4, 20):
        rc, out = spawn(["--mode", "read", "--slot", str(i), "--setcur", str(setcur),
                         "--file", str(path)])
        tag = "HIT" if rc == 0 and out.startswith("OK ") else ("越界" if rc in (3221225477, -1073741819) else f"exit {rc}")
        print(f"  slot {i:2d}: {tag}" + (f"  {out[3:]}" if tag == "HIT" else ""))


if __name__ == "__main__":
    main()
