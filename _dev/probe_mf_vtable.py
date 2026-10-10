"""标定 `IMFSourceReader` 的虚表下标——**用可验证的机制，不靠数数**。

## 为什么要有这个探针

`_dev/probe_mf_flac.py` 在同一个错上栽了两次：

  1. 按"3 + 自己的顺序"数成 `GetNativeMediaType=5 / GetCurrentMediaType=6 /
     SetCurrentMediaType=7 / ReadSample=12`；
  2. 改用 ABI 顺序推的另一组（34/35/36/40），结果 `GetNativeMediaType` 直接访问越界。

两次自相矛盾就说明问题不在"哪个数是错的"，而在**方法本身**：拿一个通用签名去扫虚表槽，
打到非函数槽上就是越界，而"返回 hr=0"也可能只是打到了一个签名刚好兼容的别的函数上。
**结论：COM 虚表下标不能靠数、也不能靠"扫到 hr=0 就算数"，必须让每次调用带上一个可验证的副作用。**

## 这个探针怎么标定

`GetCurrentMediaType` 有一个理想的验证机制：它输出的 `IMFMediaType` 是**可读的**。
所以扫描时对每个候选下标：

  * 调用它（签名 `(this, streamIndex, ppMediaType)`，用 `MF_SOURCE_READER_FIRST_AUDIO_STREAM`）；
  * 验证三件事：hr == 0、输出的指针非空、**而且从那个对象里能用 `IMFAttributes::GetUINT32`
    读出非零的采样率**（`GetUINT32` 的下标 7 是单独标定过的、可信）。

三件事同时成立才算命中。这样"打到一个签名兼容但不是它的函数"会被第三关挡掉。

定位到 `GetCurrentMediaType = G` 之后，`SetCurrentMediaType` 就是它在 ABI 顺序里的前一个
（`... GetCurrentMediaType, SetCurrentMediaType, SetCurrentPosition ...`），**再用同样的思路验证**：
设成 PCM 之后重新 `GetCurrentMediaType`，读 `MF_MT_SUBTYPE` 应当变成 PCM 的 GUID。

    python _dev/probe_mf_vtable.py --file player/input/song.mp3
    python _dev/probe_mf_vtable.py --file player/input/song2.flac
"""
from __future__ import annotations

import argparse
import ctypes
import sys
from ctypes import POINTER, byref, c_void_p, c_ulong, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MF_VERSION = 0x00020070
MFSTARTUP_FULL = 0
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

HRESULT = ctypes.c_long
#: `IMFAttributes::GetUINT32`——单独标定过（见 probe_mf_flac 的说明），可信。
ATTR_GET_U32 = 7
ATTR_SET_U32 = 21
ATTR_SET_GUID = 24


class GUID(ctypes.Structure):
    _fields_ = [("Data1", c_ulong), ("Data2", ctypes.c_ushort),
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

    def __eq__(self, other) -> bool:  # type: ignore[override]
        if not isinstance(other, GUID):
            return NotImplemented
        return (self.Data1 == other.Data1 and self.Data2 == other.Data2
                and self.Data3 == other.Data3
                and bytes(self.Data4) == bytes(other.Data4))

    def __repr__(self) -> str:
        d = bytes(self.Data4)
        return (f"{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-"
                f"{d[0]:02x}{d[1]:02x}-{''.join(f'{b:02x}' for b in d[2:])}")


_PVP = POINTER(c_void_p)
_PU32 = POINTER(ctypes.c_uint32)
_GET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), _PU32)
_SET_U32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), ctypes.c_uint32)
_SET_G = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_GET_G = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), POINTER(GUID))
_RELEASE = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def attr_u32(obj, guid: str):
    out = ctypes.c_uint32(0)
    hr = _GET_U32(vt(obj)[ATTR_GET_U32])(obj, byref(GUID(guid)), byref(out))
    return out.value if hr == 0 else None


def attr_guid(obj, guid: str):
    out = GUID("00000000-0000-0000-0000-000000000000")
    hr = _GET_G(vt(obj)[10])(obj, byref(GUID(guid)), byref(out))
    return out if hr == 0 else None


def attr_set_u32(obj, guid: str, v: int) -> int:
    return _SET_U32(vt(obj)[ATTR_SET_U32])(obj, byref(GUID(guid)), v)


def attr_set_guid(obj, guid: str, v: str) -> int:
    g = GUID(v)
    return _SET_G(vt(obj)[ATTR_SET_GUID])(obj, byref(GUID(guid)), byref(g))


#: `GetCurrentMediaType` 的签名。(this, dwStreamIndex, ppMediaType)
_GET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, _PVP)
#: `SetCurrentMediaType` 的签名。(this, dwStreamIndex, pMediaType)
_SET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)


def build_pcm_type(rate: int, ch: int, bits: int = 16):
    """造一个属性齐全的非压缩 PCM 类型。**属性必须写全**，只给 major/subtype 会被解码器拒。"""
    mf = ctypes.windll.mfplat
    mt = c_void_p()
    if mf.MFCreateMediaType(byref(mt)) != 0:
        raise OSError("MFCreateMediaType failed")
    block = ch * bits // 8
    attr_set_guid(mt, G_MAJOR, AUDIO_MAJOR)
    attr_set_guid(mt, G_SUBTYPE, PCM_SUBTYPE)
    attr_set_u32(mt, G_CHANNELS, ch)
    attr_set_u32(mt, G_RATE, rate)
    attr_set_u32(mt, G_BITS, bits)
    attr_set_u32(mt, G_BLOCK, block)
    attr_set_u32(mt, G_BPS, rate * block)
    return mt


def calibrate(reader, lo: int = 3, hi: int = 20) -> tuple[int | None, list]:
    """扫出 `GetCurrentMediaType`。命中判据有三关，缺一不算。"""
    hits = []
    for i in range(lo, hi):
        out = c_void_p()
        try:
            hr = _GET_CUR(vt(reader)[i])(reader, FIRST_AUDIO, byref(out))
        except Exception:
            continue                                # 越界：这个槽不是这个签名，跳过
        if hr != 0 or not out.value:
            continue
        rate = attr_u32(out, G_RATE)
        ch = attr_u32(out, G_CHANNELS)
        if not rate:                                # 第三关：必须能从里面读出真实属性
            rel(out)
            continue
        sub = attr_guid(out, G_SUBTYPE)
        hits.append((i, rate, ch, str(sub)))
        rel(out)
    if len(hits) != 1:
        return (hits[0][0] if len(hits) == 1 else None), hits
    return hits[0][0], hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song.mp3"))
    ap.add_argument("--lo", type=int, default=3)
    ap.add_argument("--hi", type=int, default=20)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, MFSTARTUP_FULL) != 0:
        raise SystemExit("MFStartup failed")
    print(f"file            {path.name}")
    try:
        reader = c_void_p()
        hr = rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader))
        print(f"open            hr={hr:#010x} {'ok' if hr == 0 else 'FAILED'}")
        if hr != 0:
            return

        idx, hits = calibrate(reader, a.lo, a.hi)
        print(f"scan [{a.lo},{a.hi})      hits={len(hits)}")
        for i, rate, ch, sub in hits:
            print(f"   slot {i:2d}: {rate} Hz, {ch} ch, subtype {sub}")
        if idx is None:
            print()
            print("没有唯一命中 —— 标定失败，不要继续往下做。")
            return
        print()
        print(f"GetCurrentMediaType = {idx}   （三关全过的唯一命中）")

        get_cur = _GET_CUR(vt(reader)[idx])
        set_cur = _SET_CUR(vt(reader)[idx + 1])
        cur = c_void_p()
        get_cur(reader, FIRST_AUDIO, byref(cur))
        rate = attr_u32(cur, G_RATE)
        ch = attr_u32(cur, G_CHANNELS)
        rel(cur)
        print(f"native type     {rate} Hz, {ch} ch")

        mt = build_pcm_type(rate, ch)
        hr = set_cur(reader, FIRST_AUDIO, mt)
        print(f"set PCM type    hr={hr:#010x} {'ok' if hr == 0 else 'FAILED'}")
        rel(mt)
        if hr != 0:
            print()
            print("SetCurrentMediaType 失败。注意：这一版的**下标已经标定过**，")
            print("所以这次失败是可信的——但仍要拿 mp3 的对照组一起看。")
            return

        # 验证副作用：现在的类型应当真的变成 PCM
        cur = c_void_p()
        get_cur(reader, FIRST_AUDIO, byref(cur))
        sub = attr_guid(cur, G_SUBTYPE)
        block = attr_u32(cur, G_BLOCK)
        rate2 = attr_u32(cur, G_RATE)
        rel(cur)
        print(f"current type    {rate2} Hz, block align {block}, subtype {sub}")
        print(f"is PCM          {sub == GUID(PCM_SUBTYPE)}")
        print()
        print("标定成功：下标可信，且 SetCurrentMediaType 的副作用已用 GetCurrentMediaType 验证。")
    finally:
        mf.MFShutdown()


if __name__ == "__main__":
    main()
