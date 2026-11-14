# Reverse Engineering Crash Audit: Free Fire 1.39 Match Startup & Runtime Forensics

Consolidated technical report on native signals, IL2CPP memory dereferencing, coroutine scheduling, and asset streaming across Slices 1 through 4.

---

## 1. Executive Summary & Forensic Context

During initial match transition tests on Android x86 emulation (BlueStacks Nougat/Pie), two critical failure classes were encountered:
1. **Fatal Signal 6 (`SIGABRT`) in `UnityMain`**: Preceded by `libc: invalid pthread_t 0xXXXX passed to libc`.
2. **Fatal Signal 11 (`SIGSEGV SEGV_MAPERR 0x0`) in `UnityMain`**: Null pointer dereference during `GCommon.GameEngine.LoadLoadingScene`.

Simultaneously, developer logs continuously emitted the warning:
```text
W Unity : No Such Navigation COW.UICustomRoomController
(Filename: ./artifacts/generated/Android/runtime/DebugBindings.gen.cpp Line: 51)
```

This audit formalizes the exact root causes, assembly-level disassembly, and resolutions discovered across four forensic reverse engineering investigations (Slices 1 to 4).

---

## 2. Investigation Slices

### Slice 1: `MatchmakingSussNtf` Deserialization & Protobuf Schemas
- **IL2CPP Artifact**: `dump/dump.cs` TypeDef [5877], line 123084 (`tcp.MatchmakingSussNtf`).
- **Memory Footprint**: 12 auto-property backing fields:
  ```csharp
  // TypeDef [5877]: tcp.MatchmakingSussNtf
  namespace tcp {
      public class MatchmakingSussNtf {
          public object <match_id>k__BackingField;           // Field [29718] (uint64)
          public object <server_addr>k__BackingField;        // Field [29719] (string: "ip:port")
          public object <secret>k__BackingField;             // Field [29720] (string hex)
          public object <prepare_token>k__BackingField;      // Field [29721] (string hex)
          public object <sleep_ms>k__BackingField;           // Field [29722] (uint32)
          public object <map_id>k__BackingField;             // Field [29723] (uint32: 1 = Bermuda)
          public object <game_mode>k__BackingField;          // Field [29724] (uint32: 1 = BR)
          public object <match_mode>k__BackingField;         // Field [29725] (uint32: 1 = Solo)
          public object <use_cache>k__BackingField;          // Field [29726] (bool: false)
          public object <level_visual_style>k__BackingField; // Field [29727] (uint32: 1)
          public object <difficulty>k__BackingField;         // Field [29728] (uint32)
          public object <first_login>k__BackingField;        // Field [29729] (bool)
      }
  }
  ```
- **Vulnerability / Crash Vector**:
  When the lobby server dispatched `MatchmakingSussNtf` via TCP `proto_3/cmd_5`, mismatched protobuf field numbers or primitive types (such as emitting `use_cache` as a 32-bit integer instead of boolean, or passing null for `level_visual_style`) caused the IL2CPP internal protobuf deserializer to fail silently or populate null references inside `COW.GameFacade` (TypeDef [3473]).
- **Root Cause & Fix**:
  Strict protobuf field alignment ensures every backing field is populated. If `server_addr` does not follow the exact `"IP:PORT"` syntax, `GameFacade.GameServerAddr` and `GameFacade.GameServerPort` fail parsing, resulting in an unhandled exception when initializing `GCommon.UDPSession`.

---

### Slice 2: `GameEngine.LoadLoadingScene` / `LoadAndRun` Coroutine Desync
- **IL2CPP Artifacts**:
  - `GCommon.GameEngine.LoadLoadingScene` (Method [70853], line 198934).
  - `GCommon.GameEngine.LoadAndRun` (Method [70847] / [70851]).
  - Coroutine iterator `<LoadLoadingScene>c__Iterator1` (TypeDef [9437], line 198960).
  - Coroutine cleanup iterator `<CleanAssets>c__Iterator0` (TypeDef [9436], line 198941).
- **Asynchronous Execution Model**:
  ```mermaid
  sequenceDiagram
      autonumber
      participant UI as UIFrontEndScene
      participant GE as GameEngine
      participant Clean as <CleanAssets>c__Iterator0
      participant Load as <LoadLoadingScene>c__Iterator1
      participant MG as COW.MatchGame

      UI->>GE: LoadAndRun()
      GE->>Clean: CleanAssets()
      Note over Clean: Iterates & yields null across multiple frames
      GE->>Load: LoadLoadingScene()
      Note over Load: Polls sceneLoadState
      Clean-->>GE: Cleanup Complete (AfterCleanAssets)
      Load-->>GE: Bermuda Scene AsyncLoad Ready
      GE->>MG: OnAwake() & OnSceneLoaded()
  ```
- **State Desync Discovery**:
  `GameEngine.LoadAndRun` initiates scene asset unloading concurrently with `LoadLoadingScene`. If incoming combat UDP packets (e.g. Opcode 130 or Opcode 101) arrive before `<CleanAssets>c__Iterator0.MoveNext()` returns `false`, `COW.MatchGame.CurrentGame` is accessed while in an intermediate null state.
- **Resolution**:
  Combat packet gating: UDP server delays match start packets until the client explicitly completes the loading sequence or finishes the 3-second `m_FakeLoading` animation window.

---

### Slice 3: `LevelObjectManager` and `mUseAB` Streaming Dependencies
- **IL2CPP Artifacts**:
  - `COW.MatchGame.mUseAB` (Field [18093], line 71019).
  - `COW.MatchGame.mSceneABPath` (Field [18095]) & `mStreamSceneAbPath` (Field [18096]).
  - `COW.GameFacade.CurrentLevelObjectManager()` (Method [26098]).
- **Asset Streaming Mechanism**:
  `MatchGame` evaluates the `mUseAB` (Use AssetBundle) flag to decide how Bermuda terrain geometry, navmeshes, and item prefabs are fetched:
  - If `mUseAB == true`: The engine queries external downloadable asset bundles from `/sdcard/Android/data/com.dts.freefireth/files/gameassetbundles/`.
  - If `mUseAB == false`: The engine streams directly from built-in package assets (`assets/bin/Data/sharedassets4.assets`).
- **The `SEGV_MAPERR 0x0` Null Pointer Mechanism**:
  When `mUseAB` was set to true without the corresponding `.bundle` files mounted in the client's virtual filesystem, `COW.MatchGame.SetSceneABInfo()` returned a null AssetBundle handle. Downstream, `LevelObjectManager.InitGRIData()` attempted to dereference:
  ```assembly
  mov ecx, [eax + 0x18]  ; eax = null AssetBundle pointer -> Fault Address: 0x00000000
  mov edx, [ecx + 0x04]  ; SEGV_MAPERR
  ```
- **Resolution**:
  Enforce `mUseAB = false` in `GameFacade` and `MatchmakingSussNtf` (`use_cache = false`), directing the engine to load Bermuda geometry from base APK assets.

---

### Slice 4: `UICustomRoomController` Non-Fatal Navigation Fallback
- **IL2CPP Artifact**: `COW.UICustomRoomController` (TypeDef [6550], line 137451).
- **Log Observation**:
  ```text
  W Unity : No Such Navigation COW.UICustomRoomController
  (Filename: ./artifacts/generated/Android/runtime/DebugBindings.gen.cpp Line: 51)
  ```
- **Router Analysis**:
  `UICustomRoomController` manages custom private rooms (solo, duo, quad custom matches). When `proto_3/cmd_7` (`GAMEOPENINGINFO`) arrives or when `UIFrontEndScene` cleans up open dialogs before launching the match loading screen:
  1. The navigation router (`UINavigationUtil`) traverses `UIBaseScene.m_NavigationControllersMap`.
  2. Because custom rooms are dynamically registered overlay dialogs rather than root navigation nodes, the router logs a warning and falls back to the parent stack.
- **Audit Verdict**:
  **Non-fatal**. This log does not corrupt memory, does not throw native exceptions, and is an expected diagnostic message during UI transitions.

---

## 3. Disassembly Forensics: The `invalid pthread_t` SIGABRT (Bionic libc)

In every crash run following UDP packet dispatch, Android libc triggered `SIGABRT`:
```text
11-14 12:32:46.426 18819 20106 E CrashReport-Native: Failed to get JNIEnv.
11-14 12:32:46.426 18819 20106 F libc    : invalid pthread_t 0x4e8a passed to libc
11-14 12:32:46.426 18819 20106 F libc    : Fatal signal 6 (SIGABRT), code -6 (SI_TKILL) in tid 20106 (UnityMain)
```

### 3.1 Disassembly of `libBugly.so:0x5ab0`
Reverse engineering Tencent Bugly (`apk/extracted/lib/x86/libBugly.so`) revealed an architecture bug in its custom signal handler:
```assembly
.text:00005AB0  call    gettid          ; Returns Linux Kernel TID in EAX (e.g. 20106 / 0x4e8a)
.text:00005AB5  mov     edx, [esp+20h]  ; edx = signal number (SIGABRT=6, SIGSEGV=11)
.text:00005AB9  mov     [esp], eax      ; PUSH EAX AS PTHREAD_T! (Fatal architectural flaw)
.text:00005ABC  mov     [esp+4], edx    ; signal
.text:00005AC0  call    pthread_kill    ; pthread_kill((pthread_t)tid, sig)
```

### 3.2 Bionic libc Validation Failure
On Android (Bionic libc), `pthread_t` is a typed pointer to an internal structure:
```c
struct pthread_internal_t* __pthread_internal_find(pthread_t thread_id) {
    for (pthread_internal_t* cur = g_thread_list; cur != NULL; cur = cur->next) {
        if (cur == (pthread_internal_t*)thread_id) return cur;
    }
    return NULL;
}
```
When Bugly passes integer TID `0x4e8a` as a pointer, libc finds no match in `g_thread_list`, triggers `async_safe_fatal("invalid pthread_t %p passed to libc", thread_id)`, and issues `tgkill(pid, tid, SIGABRT)`.

### 3.3 What Caused Bugly to Trigger?
Bugly was triggered by two upstream wire layout mismatches in `server/combat/combat_opcodes.py`:
1. **Opcode Numbering Mismatch**: Sending Opcode `130` (`RUDP_LANDMINE_RESYNC` in Barbosa enum) instead of `31` (`RUDP_JOIN_MATCH_FINISHED`) caused `il2cpp_class_is_assignable_from` to throw an unhandled `InvalidCastException`.
2. **Wire Codec Size Mismatch**: Opcode 101 (`message.ae zaPn`, TypeDef [4579]) had clothes count serialized as a 2-byte short instead of 4-byte `Int32`, causing `ReadInt32()` to interpret payload bytes as 2.32 billion elements, instantly exhausting heap memory.

---

## 4. Summary of Fixes Applied

| Subsystem | Root Vulnerability | Applied Fix | Verification Status |
| :--- | :--- | :--- | :---: |
| **Opcode Mapping** | Enum offset mix-up (Wire vs Index) | Standardized authentic 266-opcode catalog from TypeDef [4464] | **VERIFIED** |
| **Opcode 130 Wire Codec** | Missing trailing Barbosa collection fields | Pack exact 89-byte structure (`<iQQIBiHii hffffffff iiii`) | **VERIFIED** |
| **Opcode 101 Wire Codec** | Clothes array Int32 count interpretation | Pack exact 4-byte Int32 length headers for clothes & skills | **VERIFIED** |
| **Asset Streaming** | External bundle null pointer (`mUseAB`) | Force `use_cache = false` and built-in asset resolution | **VERIFIED** |
| **Signal Handling** | Bugly TID-as-pthread_t abort | Eliminating unhandled IL2CPP exceptions prevents handler trigger | **VERIFIED** |
