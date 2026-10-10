"""Is there any audio engine on this machine that will actually decode the new masters?

The player's music comes from Windows' own MCI (`pv_audio.py`), and the whole reason that is acceptable
is the module's own measurement: MCI plays `input/song.mp3` and its `position` is a usable clock.

The two new masters in `input/` are FLAC, and MCI does not know the format - it fails to open them at
all. So before designing a replacement, find out what the machine *does* have. Three candidates, in the
order they would cost the player:

  1. **MCI** - the incumbent. mp3 only, ~100 ms position granularity, ~237 ms decoder-lead constant.
  2. **Media Foundation** (`MFStartup` + a `IMFSourceReader`) - ships with Windows and may carry the
     FLAC byte-stream handler, which would give arbitrary sample-rate/bits and a real seek.
  3. **`waveOut` + our own decode** - the fallback: a plain PCM sink, with the decode done in Python.

This probe answers (2) with a direct COM activation request rather than an inference from the file
extension: `MFCreateSourceReaderFromURL` succeeds only if a handler claims the file. It never plays
anything and never leaves a device open.

    python _dev/probe_audio_backend.py
    python _dev/probe_audio_backend.py --file input/song2.flac
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
from ctypes import POINTER, byref, c_void_p, c_ulong, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MF_VERSION = 0x00020070
MFSTARTUP_FULL = 0
MF_SOURCE_READER_FIRST_AUDIO_STREAM = 0xFFFFFFFD
MF_SOURCE_READER_ENABLE_ADVANCED_VIDEO_PROCESSING = 0x00000001


class GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s: str) -> None:
        super().__init__()
        s = s.strip("{}")
        parts = s.split("-")
        self.Data1 = int(parts[0], 16)
        self.Data2 = int(parts[1], 16)
        self.Data3 = int(parts[2], 16)
        rest = parts[3] + parts[4]
        for i in range(8):
            self.Data4[i] = int(rest[i * 2:i * 2 + 2], 16)


IID_IMFSourceReader = GUID("70ae66f2-c809-4e4f-8915-bdcb406b7993")
IID_IMFMediaType = GUID("44ae0fa8-ea31-4109-8d2e-4cae4997c555")
MFMediaType_Audio = GUID("73647561-0000-0010-8000-00aa00389b71")
MF_MT_MAJOR_TYPE = GUID("48eba18e-f8c9-4687-bf11-0a74c9f96a8f")
MF_MT_SUBTYPE = GUID("f7e34c9a-42e8-4714-b74b-cb29d72c35e5")
MF_MT_AUDIO_NUM_CHANNELS = GUID("37e48bf5-645e-4c5b-89de-ada9e29b696a")
MF_MT_AUDIO_SAMPLES_PER_SECOND = GUID("5faeeae7-0290-4c31-9e8a-c534f68d9dba")
MF_MT_AUDIO_BITS_PER_SAMPLE = GUID("f2deb57f-40fa-4764-aa33-ed4f2d1ff669")
MF_MT_FRAME_SIZE = GUID("1652c33d-d6b2-4012-b834-72030849a37d")


def _vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", action="append",
                    help="file to test (default: every audio file in input and input/song.mp3)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    files = a.file or [str(ROOT / "player" / "input" / n)
                       for n in ("song.mp3", "song2.flac", "song3.flac")]
    print("=== MCI (the incumbent) ===")
    if os.name == "nt":
        winmm = ctypes.windll.winmm
        buf = ctypes.create_unicode_buffer(600)
        for f in files:
            p = Path(f)
            if not p.exists():
                print(f"  {p.name:14s} (missing)")
                continue
            path = p.as_posix()
            r = winmm.mciSendStringW(f'open "{path}" type mpegvideo alias PR', buf, 599, None)
            if r == 0:
                winmm.mciSendStringW("status PR length", buf, 599, None)
                print(f"  {p.name:14s} mpegvideo OPEN ok   length={buf.value} ms")
                winmm.mciSendStringW("close PR", None, 0, None)
            else:
                err = ctypes.create_unicode_buffer(600)
                winmm.mciGetErrorStringW(r, err, 599)
                print(f"  {p.name:14s} mpegvideo FAIL     {err.value}")
    else:
        print("  not Windows")

    print()
    print("=== Media Foundation source reader ===")
    if os.name != "nt":
        print("  not Windows")
        return
    try:
        mf = ctypes.windll.mfplat
    except OSError as exc:
        print(f"  mfplat unavailable: {exc}")
        return
    try:
        # the source reader lives in mfreadwrite, not mfplat
        mfrw = ctypes.windll.mfreadwrite
    except OSError as exc:
        print(f"  mfreadwrite unavailable: {exc}")
        return
    hr = mf.MFStartup(MF_VERSION, MFSTARTUP_FULL)
    print(f"  MFStartup hr={hr:#010x} ({'ok' if hr == 0 else 'FAILED'})")
    if hr != 0:
        return
    try:
        for f in files:
            p = Path(f)
            if not p.exists():
                print(f"  {p.name:14s} (missing)")
                continue
            reader = c_void_p()
            hr = mfrw.MFCreateSourceReaderFromURL(c_wchar_p(p.as_posix()), None, byref(reader))
            if hr != 0:
                print(f"  {p.name:14s} no handler  (hr={hr:#010x})")
                continue
            vt = _vt(reader)
            # the vtable indices that matter, after IUnknown's three:
            #   3 GetStreamSelection  4 SetStreamSelection  5 GetNativeMediaType
            #   6 GetCurrentMediaType  7 SetCurrentMediaType  ...
            get_type = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, c_ulong, POINTER(c_void_p))(vt[6])
            mt = c_void_p()
            hr = get_type(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM, byref(mt))
            info = ""
            if hr == 0 and mt:
                mvt = _vt(mt)
                get_u32 = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(GUID),
                                             POINTER(ctypes.c_uint32))(mvt[4])
                get_u64 = ctypes.WINFUNCTYPE(ctypes.c_long, c_void_p, POINTER(GUID),
                                             POINTER(ctypes.c_uint64))(mvt[5])
                ch = ctypes.c_uint32()
                sr = ctypes.c_uint32()
                bps = ctypes.c_uint32()
                get_u32(mt, byref(MF_MT_AUDIO_NUM_CHANNELS), byref(ch))
                get_u32(mt, byref(MF_MT_AUDIO_SAMPLES_PER_SECOND), byref(sr))
                get_u32(mt, byref(MF_MT_AUDIO_BITS_PER_SAMPLE), byref(bps))
                info = f"{sr.value} Hz, {ch.value} ch, {bps.value} bit"
                rel = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(mvt[2])
                rel(mt)
            release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(vt[2])
            release(reader)
            print(f"  {p.name:14s} HANDLER OK   {info}")
    finally:
        mf.MFShutdown()


if __name__ == "__main__":
    main()
