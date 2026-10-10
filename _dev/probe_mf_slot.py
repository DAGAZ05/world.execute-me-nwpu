"""在**子进程**里试一个虚表槽——这样"打错槽"的访问越界只会杀掉子进程，不会带走标定本身。

Windows 上访问越界是进程级的（SEH），Python 的 `try/except` 拦不住它。所以就地扫描
虚表是**不可能安全**的：`_dev/probe_mf_vtable.py` 自己就这么死过一次。

这个模块提供两件事：

  * `try_slot(idx, ...)`：把自己当成一个一次性子进程跑（`--slot N`），成功就打印
    `OK <json>`，失败/越界就非零退出。父进程 `--scan` 用 `subprocess` 逐个试，
    于是"哪个槽是 `GetCurrentMediaType`"变成一个**可以扫的问题**。
  * 判定标准不只看 hr：还要能从返回的 `IMFMediaType` 里读出非零采样率
    （`IMFAttributes::GetUINT32` 的下标 7 是单独标定过的、可信）。

    python _dev/probe_mf_slot.py --scan --file player/input/song.mp3
    python _dev/probe_mf_slot.py --slot 6 --file player/input/song.mp3     （单个，可被父进程调用）
"""
from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
from ctypes import POINTER, byref, c_void_p, c_ulong, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MF_VERSION = 0x00020070
FIRST_AUDIO = 0xFFFFFFFD
G_RATE = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
G_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"
ATTR_GET_U32 = 7          # 单独标定过，可信（见 probe_mf_flac 的说明）

HRESULT = ctypes.c_long
_PVP = POINTER(c_void_p)
_PU32 = POINTER(ctypes.c_uint32)


class GUID(ctypes.Structure):
    """**必须是一个真的 Structure，不能拿 `(c_ubyte*16)` 顶替。**

    第一版就是这么错的：`IMFAttributes::GetUINT32` 期望第二个参数是 `REFGUID`，
    而 `byref((c_ubyte*16)(...))` 传进去的是一个"16 字节数组的指针"——形状对、类型不对，
    于是调用失败，扫描结果全变成"no attributes"，把 slot 6 这个真命中给否掉了。
    ctypes 里这种错误没有报错，只有"读不到"。
    """
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
#: 候选签名：GetCurrentMediaType(this, dwStreamIndex, ppMediaType)
_CAND = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, _PVP)


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def rel(obj) -> None:
    try:
        _RELEASE(vt(obj)[2])(obj)
    except Exception:
        pass


def try_slot(path: Path, idx: int) -> None:
    """试一试 `vt[idx]` 是不是 `GetCurrentMediaType`。成功打印 OK <json>。"""
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, 0) != 0:
        raise SystemExit("MFStartup failed")
    reader = c_void_p()
    hr = rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader))
    if hr != 0:
        raise SystemExit(f"open failed {hr:#x}")
    out = c_void_p()
    hr = _CAND(vt(reader)[idx])(reader, FIRST_AUDIO, byref(out))
    if hr != 0 or not out.value:
        raise SystemExit(1)
    # 第三关：从返回的对象里读属性。做不到就不是 GetCurrentMediaType。
    rate = ctypes.c_uint32(0)
    ch = ctypes.c_uint32(0)
    ok_rate = _GET_U32(vt(out)[ATTR_GET_U32])(out, byref(GUID(G_RATE)), byref(rate)) == 0
    ok_ch = _GET_U32(vt(out)[ATTR_GET_U32])(out, byref(GUID(G_CHANNELS)), byref(ch)) == 0
    rel(out)
    if not (ok_rate and rate.value):
        raise SystemExit(2)
    print("OK " + json.dumps({"slot": idx, "rate": rate.value, "channels": ch.value}))


#: `SetCurrentMediaType(this, dwStreamIndex, pMediaType)`
_SET_CUR = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)
#: `ReadSample(this, dwStreamIndex, dwControlFlags, pdwActualStreamIndex, pdwStreamFlags,
#:            pllTimestamp, ppSample)`
_READ = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                           _PU32, _PU32, POINTER(ctypes.c_int64), _PVP)
#: `GetNativeMediaType(this, dwStreamIndex, dwMediaTypeIndex, ppMediaType)`
_GET_NATIVE = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, ctypes.c_uint32, _PVP)
#: `IMFSample::GetBuffer`
_S_GET_BUFFER = ctypes.WINFUNCTYPE(HRESULT, c_void_p, _PVP, _PU32, _PU32)


def _open(path: Path):
    mf = ctypes.windll.mfplat
    rw = ctypes.windll.mfreadwrite
    if mf.MFStartup(MF_VERSION, 0) != 0:
        raise SystemExit("MFStartup failed")
    reader = c_void_p()
    hr = rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader))
    if hr != 0:
        raise SystemExit(f"open failed {hr:#x}")
    return mf, reader


def try_setcur(path: Path, idx: int) -> None:
    """`SetCurrentMediaType` 的判据：**用原生类型设回去必须成功**。

    这个判据比"设 PCM 成功"强得多：它不依赖解码器愿不愿意给 PCM，
    只依赖"这是不是那个函数"——把原生类型设回它自己，任何实现都必须接受。
    """
    mf, reader = _open(path)
    try:
        nt = c_void_p()
        hr = _GET_NATIVE(vt(reader)[R_GET_NATIVE_HINT])(reader, FIRST_AUDIO, 0, byref(nt))
        if hr != 0 or not nt.value:
            raise SystemExit(3)
        hr = _SET_CUR(vt(reader)[idx])(reader, FIRST_AUDIO, nt)
        rel(nt)
        if hr != 0:
            raise SystemExit(1)
        print("OK " + json.dumps({"slot": idx}))
    finally:
        rel(reader)
        mf.MFShutdown()


def try_read(path: Path, idx: int) -> None:
    """`ReadSample` 的判据：调一次必须返回 hr==0，且**指针是 NULL**（没有样本）或
    能通过 `IMFSample::GetBuffer` 读出长度 > 0。"""
    mf, reader = _open(path)
    try:
        actual = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        ts = ctypes.c_int64()
        samp = c_void_p()
        hr = _READ(vt(reader)[idx])(reader, FIRST_AUDIO, 0, byref(actual), byref(flags),
                                    byref(ts), byref(samp))
        if hr != 0:
            raise SystemExit(1)
        if not samp.value:
            # 没有样本也算这个槽存在（EOS / 需要更多数据），但要让父进程知道
            print("OK " + json.dumps({"slot": idx, "bytes": 0, "note": "null sample"}))
            return
        buf = c_void_p()
        mx = ctypes.c_uint32()
        ln = ctypes.c_uint32()
        ok = _S_GET_BUFFER(vt(samp)[_S_GET_BUFFER_IDX])(samp, byref(buf), byref(mx), byref(ln)) == 0
        rel(samp)
        if not ok:
            raise SystemExit(2)
        print("OK " + json.dumps({"slot": idx, "bytes": ln.value}))
    finally:
        rel(reader)
        mf.MFShutdown()


R_GET_NATIVE_HINT = 6      # 标定值：GetNativeMediaType 在这个壳里也是 6（见 docstring）
_S_GET_BUFFER_IDX = 3


def scan(path: Path, lo: int, hi: int) -> None:
    me = Path(__file__).resolve()
    hits = []
    for i in range(lo, hi):
        r = subprocess.run([sys.executable, str(me), "--slot", str(i), "--file", str(path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.startswith("OK "):
            info = json.loads(r.stdout[3:])
            hits.append(info)
            print(f"  slot {i:2d}: hit  {info['rate']} Hz, {info['channels']} ch")
        else:
            tag = {1: "hr!=0", 2: "no attributes"}.get(r.returncode, f"exit {r.returncode}")
            print(f"  slot {i:2d}: --   {tag}")
    print()
    if len(hits) == 1:
        print(f"GetCurrentMediaType = {hits[0]['slot']}  （唯一命中）")
        print(f"（按 ABI 顺序，SetCurrentMediaType = {hits[0]['slot'] + 1}）")
    else:
        print(f"命中 {len(hits)} 个，不唯一 —— 不要据此下结论。")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song.mp3"))
    ap.add_argument("--slot", type=int, help="internal: try one slot")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--lo", type=int, default=3)
    ap.add_argument("--hi", type=int, default=20)
    a = ap.parse_args()
    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")
    if a.slot is not None:
        try_slot(path, a.slot)
        return
    print(f"file   {path.name}")
    print(f"scan   [{a.lo}, {a.hi})  每个槽一个子进程（越界只杀子进程）")
    scan(path, a.lo, a.hi)


if __name__ == "__main__":
    main()
