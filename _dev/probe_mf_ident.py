"""一次性把 `IMFSourceReader` 的槽认出来：**按"返回的对象是不是真 media type"判据**。

这个壳子里下标错了三轮，所以这一步不猜、不数，只认对象：

  * 3 参签名 `(this, streamIndex, ppMediaType)` 试每一个槽；
  * 4 参签名 `(this, streamIndex, typeIndex, ppMediaType)` 也试；
  * 对返回的指针**先用 magic 校验它确实是一个 `IMFMediaType`**：
    `IMFAttributes::GetGUID(MF_MT_MAJOR_TYPE)` 必须等于 `MFMediaType_Audio`
    （`73647561-0000-0010-8000-00aa00389b71`）。这个判据把"打到一个签名兼容但不是它的函数"
    彻底挡掉——因为只有真的 media type 才有这个属性。
  * 再读 `MF_MT_SUBTYPE` 区分"原生（压缩）类型"和"当前（输出）类型"。

每槽一个子进程（越界只杀子进程）。

    python _dev/probe_mf_ident.py --file player/input/song.mp3
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
ATTR_GET_GUID = 10
AUDIO_MAJOR = "73647561-0000-0010-8000-00aa00389b71"
G_MAJOR = "48eba18e-f8c9-4687-bf11-0a74c9f96a8f"
G_SUBTYPE = "f7e34c9a-42e8-4714-b74b-cb29d72c35e5"
G_RATE = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
G_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"

HRESULT = ctypes.c_long
_PVP = POINTER(c_void_p)
_PU32 = POINTER(ctypes.c_uint32)


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
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
#: 3 参候选
_C3 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, _PVP)
#: 4 参候选
_C4 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PVP)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def au32(obj, g: str):
    out = ctypes.c_uint32(0)
    hr = _GET_U32(vt(obj)[ATTR_GET_U32])(obj, byref(GUID(g)), byref(out))
    return out.value if hr == 0 else None


def aguid(obj, g: str):
    out = GUID()
    hr = _GET_GUID(vt(obj)[ATTR_GET_GUID])(obj, byref(GUID(g)), byref(out))
    return out if hr == 0 else None


def probe(path: Path, slot: int) -> None:
    """试一个槽的两种签名，输出所有"返回了真 media type"的结果。"""
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, 0) != 0:
        raise SystemExit("MFStartup failed")
    reader = c_void_p()
    if rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader)) != 0:
        raise SystemExit("open failed")
    out_map = []
    try:
        for tag, call in (("3arg", lambda: _C3(vt(reader)[slot])(reader, FIRST_AUDIO, byref(o3))),
                          ("4arg", lambda: _C4(vt(reader)[slot])(reader, FIRST_AUDIO, 0,
                                                                byref(o4)))):
            if tag == "3arg":
                o3 = c_void_p()
                try:
                    hr = call()
                except Exception:
                    continue
                ptr = o3
            else:
                o4 = c_void_p()
                try:
                    hr = call()
                except Exception:
                    continue
                ptr = o4
            if hr != 0 or not ptr.value:
                continue
            maj = aguid(ptr, G_MAJOR)
            if not maj or repr(maj) != AUDIO_MAJOR:
                rel(ptr)
                continue
            entry = {"sig": tag, "major": repr(maj), "subtype": repr(aguid(ptr, G_SUBTYPE)),
                     "rate": au32(ptr, G_RATE), "channels": au32(ptr, G_CHANNELS)}
            out_map.append(entry)
            rel(ptr)
    finally:
        rel(reader)
        mf.MFShutdown()
    if out_map:
        print("OK " + json.dumps({"slot": slot, "results": out_map}))
    raise SystemExit(1 if not out_map else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song.mp3"))
    ap.add_argument("--slot", type=int)
    ap.add_argument("--lo", type=int, default=3)
    ap.add_argument("--hi", type=int, default=14)
    a = ap.parse_args()
    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")
    if a.slot is not None:
        probe(path, a.slot)
        return
    me = Path(__file__).resolve()
    print(f"file   {path.name}")
    print(f"判据   返回的对象必须能读出 MF_MT_MAJOR_TYPE == MFMediaType_Audio")
    print()
    for i in range(a.lo, a.hi):
        r = subprocess.run([sys.executable, str(me), "--slot", str(i), "--file", str(path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.startswith("OK "):
            info = json.loads(r.stdout[3:])
            for e in info["results"]:
                print(f"  slot {i:2d} [{e['sig']}]: AUDIO type  subtype={e['subtype']} "
                      f"{e['rate']} Hz, {e['channels']} ch")
        elif r.returncode in (3221225477, -1073741819) or r.returncode < 0:
            print(f"  slot {i:2d}: 越界（这个槽不是这两种签名中的任何一个）")
        else:
            print(f"  slot {i:2d}: --")


if __name__ == "__main__":
    main()
