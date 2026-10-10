"""用 Media Foundation 把音频**真的解成 PCM**——先 mp3 做对照，再看 FLAC。

## 下标是标定出来的，不是数出来的

`_dev/probe_mf_slot.py` 用"每个槽一个子进程"的方式扫出 `GetCurrentMediaType = 6`
（三关判据：hr==0、指针非空、**能从里面读出非零采样率**），于是按 ABI 顺序
`SetCurrentMediaType = 7`、`GetNativeMediaType = 5`、`ReadSample = 12`。
这就是 Windows SDK 头文件里的值——**我前两轮把它们数错，第三轮又把标定本身写错**
（`GetUINT32` 的第二参数用 `(c_ubyte*16)` 顶替 `REFGUID`，形状对、类型不对，
于是所有候选都读不到属性，真命中被否掉）。这一段历史写在这里，因为它是这个文件存在的理由。

## 判据

  * **mp3 必须先通**（对照组）。mp3 在这台机器上 MF 一定能解，所以它不通就是我的错；
  * 通了以后再看 FLAC：`mp3 通 + FLAC 不通` 才是"格式限制"的证据；
  * 全程只解码到内存、丢弃，**不播放声音、不改仓库**。

    python _dev/probe_mf_pcm.py --file player/input/song.mp3 --seconds 2
    python _dev/probe_mf_pcm.py --file player/input/song2.flac --seconds 2
    python _dev/probe_mf_pcm.py --all
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
ENDOFSTREAM = 0x00000002

G_MAJOR = "48eba18e-f8c9-4687-bf11-0a74c9f96a8f"
G_SUBTYPE = "f7e34c9a-42e8-4714-b74b-cb29d72c35e5"
G_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"
G_RATE = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
G_BITS = "f2deb57f-40fa-4764-aa33-ed4f2d1ff669"
G_BLOCK = "322de230-f9eb-43bd-ab7a-ff412251541d"
G_BPS = "1aab75c8-cfef-451c-ab95-ac034b8e1731"
AUDIO_MAJOR = "73647561-0000-0010-8000-00aa00389b71"
PCM_SUBTYPE = "00000001-0000-0010-8000-00aa00389b71"

# ---- 标定值（见模块 docstring）
R_GET_NATIVE = 5
R_GET_CUR = 6
R_SET_CUR = 7
R_READ = 12
# ---- IMFAttributes（GetUINT32 单独标定过）
A_GET_U32 = 7
A_SET_U32 = 21
A_SET_GUID = 24
A_GET_GUID = 10
# ---- IMFSample
S_GET_BUFFER = 3

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

    def __repr__(self) -> str:
        d = bytes(self.Data4)
        return (f"{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-"
                f"{d[0]:02x}{d[1]:02x}-{''.join(f'{b:02x}' for b in d[2:])}")


_GET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), _PU32)
_GET_GUID = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_SET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), ctypes.c_uint32)
_SET_GUID = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
_GET_NATIVE = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PVP)
_GET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, _PVP)
_SET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)
_READ = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PU32, _PU32,
                           _PI64, _PVP)
_GET_BUFFER = ctypes.WINFUNCTYPE(HRESULT, c_void_p, _PVP, _PU32, _PU32)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def au32(obj, guid: str):
    out = ctypes.c_uint32(0)
    hr = _GET_U32(vt(obj)[A_GET_U32])(obj, byref(GUID(guid)), byref(out))
    return out.value if hr == 0 else None


def aguid(obj, guid: str):
    out = GUID("00000000-0000-0000-0000-000000000000")
    hr = _GET_GUID(vt(obj)[A_GET_GUID])(obj, byref(GUID(guid)), byref(out))
    return out if hr == 0 else None


def aset_u32(obj, guid: str, v: int) -> int:
    return _SET_U32(vt(obj)[A_SET_U32])(obj, byref(GUID(guid)), v)


def aset_guid(obj, guid: str, v: str) -> int:
    g = GUID(v)
    return _SET_GUID(vt(obj)[A_SET_GUID])(obj, byref(GUID(guid)), byref(g))


def build_pcm(rate: int, ch: int, bits: int = 16):
    """属性写全的非压缩 PCM 类型。只给 major/subtype 会被解码器拒。"""
    mf = ctypes.windll.mfplat
    mt = c_void_p()
    if mf.MFCreateMediaType(byref(mt)) != 0:
        raise OSError("MFCreateMediaType failed")
    block = ch * bits // 8
    aset_guid(mt, G_MAJOR, AUDIO_MAJOR)
    aset_guid(mt, G_SUBTYPE, PCM_SUBTYPE)
    aset_u32(mt, G_CHANNELS, ch)
    aset_u32(mt, G_RATE, rate)
    aset_u32(mt, G_BITS, bits)
    aset_u32(mt, G_BLOCK, block)
    aset_u32(mt, G_BPS, rate * block)
    return mt


def decode(path: Path, seconds: float, verbose: bool = True) -> dict:
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, 0) != 0:
        raise OSError("MFStartup failed")
    res = {"file": path.name, "open": False, "native": None, "pcm_type": False,
           "bytes": 0, "frames": 0, "sample_frames": 0, "rate": None,
           "channels": None, "block": None, "error": None}
    try:
        reader = c_void_p()
        hr = rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader))
        res["open"] = hr == 0
        if hr != 0:
            res["error"] = f"open hr={hr:#010x}"
            return res

        nt = c_void_p()
        hr = _GET_NATIVE(vt(reader)[R_GET_NATIVE])(reader, FIRST_AUDIO, 0, byref(nt))
        if hr == 0 and nt.value:
            res["native"] = (au32(nt, G_RATE), au32(nt, G_CHANNELS))
            rel(nt)

        rate = (res["native"] or (44100, 2))[0] or 44100
        ch = (res["native"] or (44100, 2))[1] or 2
        res["rate"], res["channels"] = rate, ch
        res["block"] = ch * 2

        mt = build_pcm(rate, ch)
        hr = _SET_CUR(vt(reader)[R_SET_CUR])(reader, FIRST_AUDIO, mt)
        rel(mt)
        res["pcm_type"] = hr == 0
        if hr != 0:
            res["error"] = f"SetCurrentMediaType hr={hr:#010x}"
            rel(reader)
            return res

        # 验证副作用：现在的类型应当真是 PCM
        cur = c_void_p()
        _GET_CUR(vt(reader)[R_GET_CUR])(reader, FIRST_AUDIO, byref(cur))
        if cur.value:
            res["effective"] = str(aguid(cur, G_SUBTYPE))
            res["effective_block"] = au32(cur, G_BLOCK)
            res["effective_rate"] = au32(cur, G_RATE)
            rel(cur)

        want = int(seconds * rate)
        read = _READ(vt(reader)[R_READ])
        t0 = time.perf_counter()
        ts_first = ts_last = None
        while res["sample_frames"] < want:
            actual = ctypes.c_uint32()
            flags = ctypes.c_uint32()
            ts = ctypes.c_int64()
            samp = c_void_p()
            hr = read(reader, FIRST_AUDIO, 0, byref(actual), byref(flags), byref(ts), byref(samp))
            if hr != 0:
                res["error"] = f"ReadSample hr={hr:#010x}"
                break
            if flags.value & ENDOFSTREAM:
                res["eos"] = True
                if samp.value:
                    rel(samp)
                break
            if samp.value:
                buf = c_void_p()
                mx = ctypes.c_uint32()
                ln = ctypes.c_uint32()
                if _GET_BUFFER(vt(samp)[S_GET_BUFFER])(samp, byref(buf), byref(mx), byref(ln)) == 0:
                    res["bytes"] += ln.value
                    res["sample_frames"] += ln.value // max(1, res["block"])
                    if ts_first is None:
                        ts_first = ts.value
                    ts_last = ts.value
                rel(samp)
            res["frames"] += 1
            if res["frames"] > 300000:
                break
        res["decode_s"] = time.perf_counter() - t0
        if ts_first is not None and ts_last is not None:
            res["ts_span_ms"] = (ts_last - ts_first) / 10000.0
        rel(reader)
    finally:
        mf.MFShutdown()
    return res


def report(r: dict) -> bool:
    print(f"file            {r['file']}")
    print(f"open            {'ok' if r['open'] else 'FAILED'}")
    if r["native"]:
        print(f"native type     {r['native'][0]} Hz, {r['native'][1]} ch")
    print(f"set PCM type    {'ok' if r['pcm_type'] else 'FAILED'}"
          + (f"  ({r['error']})" if r.get("error") and not r["pcm_type"] else ""))
    if r.get("effective"):
        print(f"effective type  {r['effective_rate']} Hz, block {r['effective_block']}, "
              f"subtype {r['effective']}")
    if r["pcm_type"]:
        secs = r["sample_frames"] / max(1, r["rate"])
        print(f"decoded         {r['frames']} objects, {r['bytes']} bytes = "
              f"{r['sample_frames']} sample-frames ({secs:.2f} s)")
        if r.get("ts_span_ms") is not None:
            print(f"timestamps      span {r['ts_span_ms']:.1f} ms for {secs * 1000:.1f} ms "
                  f"of audio")
        print(f"wall time       {r.get('decode_s', 0):.2f} s "
              f"({r['sample_frames'] / max(r.get('decode_s', 1e-9), 1e-9) / 1000:.0f} ksamples/s)")
    ok = bool(r["pcm_type"] and r["bytes"] > 0)
    print(f"VERDICT         {'PCM OK' if ok else 'NO PCM'}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file")
    ap.add_argument("--all", action="store_true",
                    help="mp3 (control) then both FLACs")
    ap.add_argument("--seconds", type=float, default=2.0)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    inp = ROOT / "player" / "input"
    files = ([inp / "song.mp3", inp / "song2.flac", inp / "song3.flac"] if a.all
             else [Path(a.file) if a.file else inp / "song.mp3"])
    results = []
    for f in files:
        if not f.exists():
            print(f"file            {f.name}\n  (missing)\n")
            continue
        r = decode(f, a.seconds)
        results.append((f.name, report(r)))
        print()
    if len(results) > 1:
        print("=== 判据 ===")
        for name, ok in results:
            print(f"  {name:14s} {'PCM OK' if ok else 'NO PCM'}")
        ctrl = dict(results).get("song.mp3")
        print()
        if ctrl:
            print("对照组 mp3 通了 —— 所以其余文件的结果才是关于格式本身的。")
        else:
            print("**对照组 mp3 没通 —— 说明我的调用还有错，不能据此判断任何格式。**")


if __name__ == "__main__":
    main()
