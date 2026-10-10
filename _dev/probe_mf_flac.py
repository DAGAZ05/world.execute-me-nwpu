"""FLAC 播放的可行性：Media Foundation 能不能真的把 PCM 交出来，以及它的时钟准不准。

批 84 已经实测两件事（`_dev/probe_audio_backend.py`）：

  * Windows 的 MCI（播放器现在用的后端）**打不开这两个 FLAC**；
  * 这台机器的 **Media Foundation 认得它们**（`MFCreateSourceReaderFromURL` 成功）。

"认得"不等于"能给 PCM"，更不等于"能当时钟"。这个探针回答剩下的两问：

  1. 把源读取器设成 **PCM 输出**，`ReadSample` 能不能真的拿到样本、拿到多少；
  2. `IMFPresentationClock` / 读取器自己报的时间戳，精度够不够当播放器的时钟
     （`pv_audio` 现在靠 MCI 的 `position`，量化步长约 100 ms）。

它**不播放任何声音**（只解码到内存后丢掉），也不改仓库里的任何东西。

    python _dev/probe_mf_flac.py
    python _dev/probe_mf_flac.py --file player/input/song3.flac --seconds 10
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from ctypes import POINTER, byref, c_void_p, c_ulong, c_wchar_p
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MF_VERSION = 0x00020070
MFSTARTUP_FULL = 0
MF_SOURCE_READER_FIRST_AUDIO_STREAM = 0xFFFFFFFD
MF_SOURCE_READERF_ENDOFSTREAM = 0x00000002
MF_MT_MAJOR_TYPE = "48eba18e-f8c9-4687-bf11-0a74c9f96a8f"
MF_MT_SUBTYPE = "f7e34c9a-42e8-4714-b74b-cb29d72c35e5"
MFAudioFormat_PCM = "00000001-0000-0010-8000-00aa00389b71"
MF_MT_AUDIO_NUM_CHANNELS = "37e48bf5-645e-4c5b-89de-ada9e29b696a"
MF_MT_AUDIO_SAMPLES_PER_SECOND = "5faeeae7-0290-4c31-9e8a-c534f68d9dba"
MF_MT_AUDIO_BLOCK_ALIGNMENT = "322de230-f9eb-43bd-ab7a-ff412251541d"
MF_MT_AUDIO_AVG_BYTES_PER_SECOND = "1aab75c8-cfef-451c-ab95-ac034b8e1731"
MF_MT_ALL_SAMPLES_INDEPENDENT = "c9173739-5e56-461c-b713-46fb995cb95f"


class GUID(ctypes.Structure):
    _fields_ = [("Data1", c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s: str) -> None:  # type: ignore[override]
        super().__init__()
        parts = s.strip("{}").split("-")
        self.Data1 = int(parts[0], 16)
        self.Data2 = int(parts[1], 16)
        self.Data3 = int(parts[2], 16)
        rest = parts[3] + parts[4]
        for i in range(8):
            self.Data4[i] = int(rest[i * 2:i * 2 + 2], 16)


HRESULT = ctypes.c_long


def vt(obj):
    return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents


class MF:
    """Media Foundation 的最小封装。

    COM 调用在 ctypes 里最容易错的地方是**虚表下标**（`IUnknown` 占前 3 个）与**argtypes**：
    `byref(x)` 是 `CArgObject`，没有 `from_param`，所以不能靠 `type(a)` 反推参数类型——
    必须像下面这样每个方法写一遍 `WINFUNCTYPE` 与 `argtypes`。
    """

    # **IMFSourceReader 继承 IMFAttributes，它的方法在很后面——而且是"标定"出来的，不是数出来的。**
    # IUnknown 占 0-2，IMFAttributes 占 3-31（实测 GetUINT32 = 7、SetUINT32 = 21 都对得上），
    # IMFSourceReader 自己的方法跟在后面。
    #
    # **实测锚点**：用一个自己建的 IMFMediaType 扫 `SetCurrentMediaType(stream, pmt)`，
    # 唯一返回 hr=0 的是 **下标 38**（其余下标要么 E_INVALIDARG、要么直接访问越界——
    # 后者说明那些槽根本不是方法）。于是按 ABI 顺序推出：
    #   32 GetStreamSelection   33 SetStreamSelection   34 GetNativeMediaType
    #   35 GetCurrentMediaType  36 SetCurrentMediaType  37 SetCurrentPosition
    #   38 GetPresentationAttribute 39 GetCharacteristics 40 ReadSample 41 Flush
    # ……但标定说 38 就是 SetCurrentMediaType，所以真实起点比 32 晚 2：起点 = 36。
    # 这里**只用标定过的那个下标**（SetCurrentMediaType = 38），其余按 ABI 顺序推并逐个用
    # "返回 hr 是否合理"验证，而不是假设。
    #
    # 教训（写下来因为踩了两轮）：**COM 虚表下标不要数，要标定。** 数错的下场是
    # `SetCurrentMediaType` 打到别的槽上，而且**对 mp3 也一样失败**——
    # "拿一个已知能用的格式做对照组"是发现这类错误的唯一办法。
    R_SET_CURRENT = 38             # 标定值（用自己建的 media type 扫出来的唯一 hr=0 槽）
    # !! 警告：上面这个 38 之前写成 7 时对 mp3 也失败，说明当时打错了槽；
    # !! 而改成 38 之后 GetNativeMediaType(34/36) 又直接访问越界。两次自相矛盾说明
    # !! **靠扫下标标定 COM 虚表在这个 ctypes 壳里不可靠**（扫的时候用的是通用签名，
    # !! 打到非函数槽上就是越界）。正确做法是用 IMFSample/IMFMediaType 的真实头文件
    # !! 对齐下标，或者干脆换一个已有明确定义的绑定。这个探针因此**只作为记录保留**，
    # !! 不作为结论依据。
    R_GET_CURRENT = 37             # ABI 顺序：SetCurrent 的前一个
    R_GET_NATIVE = 36              # 再前一个
    R_READ_SAMPLE = R_SET_CURRENT + 4   # 42

    # IMFAttributes 的下标（IUnknown 占 0-2）。**这一组最容易数错**：
    # 0 QueryInterface 1 AddRef 2 Release
    # 3 GetItem 4 GetItemType 5 CompareItem 6 Compare
    # 7 GetUINT32 8 GetUINT64 9 GetDouble 10 GetGUID
    # 11 GetStringLength 12 GetString 13 GetAllocatedString 14 GetBlobSize 15 GetBlob
    # 16 GetAllocatedBlob 17 GetUnknown 18 SetItem 19 DeleteItem 20 DeleteAllItems
    # 21 SetUINT32 22 SetUINT64 23 SetDouble 24 SetGUID 25 SetString ...
    # 第一版把 GetUINT32 当成 4、SetUINT32 当成 6、SetGUID 当成 8，于是属性读出的是垃圾
    # （"19 Hz, 19 ch"）而 SetGUID 根本没生效 —— 这正是 SetCurrentMediaType 回
    # MF_E_INVALIDMEDIATYPE 的原因。
    A_GET_U32 = 7
    A_SET_U32 = 21
    A_SET_GUID = 24

    def __init__(self) -> None:
        self.mf = ctypes.windll.mfplat
        self.rw = ctypes.windll.mfreadwrite
        hr = self.mf.MFStartup(MF_VERSION, MFSTARTUP_FULL)
        if hr != 0:
            raise OSError(f"MFStartup failed hr={hr:#x}")
        self.PU32 = POINTER(ctypes.c_uint32)
        self.PI64 = POINTER(ctypes.c_int64)
        self.PVP = POINTER(c_void_p)
        self._attr_get_u32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), self.PU32)
        self._attr_set_u32 = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID), ctypes.c_uint32)
        self._attr_set_guid = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(GUID),
                                                 POINTER(GUID))
        self._release = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
        # IMFSourceReader
        self._rd_native = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32,
                                             ctypes.c_uint32, self.PVP)
        self._rd_current = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, self.PVP)
        self._rd_set_current = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32, c_void_p)
        self._rd_read = ctypes.WINFUNCTYPE(HRESULT, c_void_p, ctypes.c_uint32,
                                           ctypes.c_uint32, self.PU32, self.PU32,
                                           self.PI64, self.PVP)
        # IMFSample: GetBuffer = 3
        self._samp_get_buffer = ctypes.WINFUNCTYPE(HRESULT, c_void_p, self.PVP,
                                                   self.PU32, self.PU32)

    def vt(self, obj):
        return ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents

    def get_native(self, reader, stream, index):
        out = c_void_p()
        fn = self._rd_native(self.vt(reader)[self.R_GET_NATIVE])
        hr = fn(reader, stream, index, byref(out))
        return hr, out

    def get_current(self, reader, stream):
        out = c_void_p()
        fn = self._rd_current(self.vt(reader)[self.R_GET_CURRENT])
        hr = fn(reader, stream, byref(out))
        return hr, out

    def set_current(self, reader, stream, mt):
        fn = self._rd_set_current(self.vt(reader)[self.R_SET_CURRENT])
        return fn(reader, stream, mt)

    def read_sample(self, reader, stream):
        actual = ctypes.c_uint32()
        flags = ctypes.c_uint32()
        ts = ctypes.c_int64()
        samp = c_void_p()
        fn = self._rd_read(self.vt(reader)[self.R_READ_SAMPLE])
        hr = fn(reader, stream, 0, byref(actual), byref(flags), byref(ts), byref(samp))
        return hr, flags.value, ts.value, samp

    def sample_bytes(self, samp):
        buf = c_void_p()
        mx = ctypes.c_uint32()
        ln = ctypes.c_uint32()
        fn = self._samp_get_buffer(self.vt(samp)[3])
        hr = fn(samp, byref(buf), byref(mx), byref(ln))
        return (ln.value if hr == 0 else None)

    def attr_u32(self, obj, guid):
        out = ctypes.c_uint32()
        fn = self._attr_get_u32(self.vt(obj)[self.A_GET_U32])
        hr = fn(obj, byref(GUID(guid)), byref(out))
        return out.value if hr == 0 else None

    def attr_set_u32(self, obj, guid, value):
        fn = self._attr_set_u32(self.vt(obj)[self.A_SET_U32])
        return fn(obj, byref(GUID(guid)), value)

    def attr_set_guid(self, obj, guid, val):
        g = GUID(val)
        fn = self._attr_set_guid(self.vt(obj)[self.A_SET_GUID])
        return fn(obj, byref(GUID(guid)), byref(g))

    def rel(self, obj):
        try:
            self._release(self.vt(obj)[2])(obj)
        except Exception:
            pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(ROOT / "player" / "input" / "song2.flac"))
    ap.add_argument("--seconds", type=float, default=6.0,
                    help="how much audio to actually decode")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    path = Path(a.file)
    if not path.exists():
        raise SystemExit(f"missing: {path}")
    mf = MF()
    try:
        reader = c_void_p()
        hr = mf.rw.MFCreateSourceReaderFromURL(c_wchar_p(path.as_posix()), None, byref(reader))
        print(f"file            {path.name}")
        print(f"open            hr={hr:#010x} {'ok' if hr == 0 else 'FAILED'}")
        if hr != 0:
            return

        # 1) 原生类型
        hr, native = mf.get_native(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM, 0)
        if hr == 0 and native:
            sr = mf.attr_u32(native, MF_MT_AUDIO_SAMPLES_PER_SECOND)
            ch = mf.attr_u32(native, MF_MT_AUDIO_NUM_CHANNELS)
            print(f"native type     {sr} Hz, {ch} ch")
            mf.rel(native)
        else:
            print(f"native type     hr={hr:#010x} (no native type)")

        # 2) 要求 PCM 输出。
        #    **必须把非压缩类型的关键属性一并写全**，只给 major/subtype 会被回
        #    MF_E_INVALIDMEDIATYPE（0x80070057 系列的那一族）：解码器的输出类型验证要看
        #    "声道数 / 采样率 / 位深 / 块对齐 / 平均字节率"，缺一项就不认。
        hr, cur0 = mf.get_current(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM)
        src_sr = mf.attr_u32(cur0, MF_MT_AUDIO_SAMPLES_PER_SECOND) or 44100
        src_ch = mf.attr_u32(cur0, MF_MT_AUDIO_NUM_CHANNELS) or 2
        if cur0:
            mf.rel(cur0)
        bits = 16
        block = src_ch * bits // 8
        mt = c_void_p()
        hr = mf.mf.MFCreateMediaType(byref(mt))
        if hr != 0:
            print(f"MFCreateMediaType failed hr={hr:#x}")
            return
        mf.attr_set_guid(mt, MF_MT_MAJOR_TYPE, "73647561-0000-0010-8000-00aa00389b71")
        mf.attr_set_guid(mt, MF_MT_SUBTYPE, MFAudioFormat_PCM)
        mf.attr_set_u32(mt, MF_MT_AUDIO_NUM_CHANNELS, src_ch)
        mf.attr_set_u32(mt, MF_MT_AUDIO_SAMPLES_PER_SECOND, src_sr)
        mf.attr_set_u32(mt, "f2deb57f-40fa-4764-aa33-ed4f2d1ff669", bits)   # BITS_PER_SAMPLE
        mf.attr_set_u32(mt, MF_MT_AUDIO_BLOCK_ALIGNMENT, block)
        mf.attr_set_u32(mt, MF_MT_AUDIO_AVG_BYTES_PER_SECOND, src_sr * block)
        mf.attr_set_u32(mt, MF_MT_ALL_SAMPLES_INDEPENDENT, 1)
        hr = mf.set_current(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM, mt)
        print(f"set PCM type    hr={hr:#010x} {'ok' if hr == 0 else 'FAILED'}"
              f"  (asked {src_sr} Hz, {src_ch} ch, {bits} bit PCM)")
        mf.rel(mt)
        if hr != 0:
            print()
            print("如果这一步失败，说明这台机器的 MF FLAC 解码器不提供非压缩 PCM 输出。")
            print("那么 FLAC 播放只剩两条路：自己解码（纯 Python，慢但可行），")
            print("或让用户装 ffmpeg 离线转成 WAV。两条都记进 增强方向.md。")
            mf.rel(reader)
            return

        hr, cur = mf.get_current(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM)
        sr = mf.attr_u32(cur, MF_MT_AUDIO_SAMPLES_PER_SECOND)
        ch = mf.attr_u32(cur, MF_MT_AUDIO_NUM_CHANNELS)
        ba = mf.attr_u32(cur, MF_MT_AUDIO_BLOCK_ALIGNMENT)
        br = mf.attr_u32(cur, MF_MT_AUDIO_AVG_BYTES_PER_SECOND)
        print(f"current type    {sr} Hz, {ch} ch, block align {ba}, avg bytes/s {br}")
        mf.rel(cur)

        # 3) ReadSample 真的读
        want = int(a.seconds * sr)
        got = 0
        samples_seen = 0
        ts_first = ts_last = None
        frames = 0
        t0 = time.perf_counter()
        while samples_seen < want:
            hr, flags, ts, samp = mf.read_sample(reader, MF_SOURCE_READER_FIRST_AUDIO_STREAM)
            if hr != 0:
                print(f"ReadSample      hr={hr:#010x} after {frames} objects")
                break
            if flags & MF_SOURCE_READERF_ENDOFSTREAM:
                print(f"ReadSample      end of stream after {frames} objects")
                if samp:
                    mf.rel(samp)
                break
            if samp and samp.value:
                n = mf.sample_bytes(samp)
                if n:
                    got += n
                    samples_seen += n // max(1, ba)
                if ts_first is None:
                    ts_first = ts
                ts_last = ts
                mf.rel(samp)
            frames += 1
            if frames > 200000:
                break
        dt = time.perf_counter() - t0
        print()
        print(f"decoded         {frames} sample objects, {got} bytes "
              f"= {samples_seen} sample-frames ({samples_seen / sr:.2f} s of audio)")
        print(f"timestamps      first {ts_first} last {ts_last} (100ns units; 10000 = 1 ms)")
        if ts_first is not None and ts_last is not None:
            span_ms = (ts_last - ts_first) / 10000.0
            audio_ms = samples_seen / sr * 1000
            ok = abs(span_ms - audio_ms) < 500
            print(f"                span {span_ms:.1f} ms for {audio_ms:.1f} ms of audio"
                  f" -> {'plausible' if ok else 'SUSPECT'}")
        print(f"wall time       {dt:.2f} s ({samples_seen / max(dt, 1e-9) / 1000:.0f} ksamples/s)")
        mf.rel(reader)
    finally:
        mf.mf.MFShutdown()


if __name__ == "__main__":
    main()
