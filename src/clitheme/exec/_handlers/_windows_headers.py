# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

import ctypes
from ctypes import wintypes
import io

# spell-checker:ignoreRegExp [A-Z]+

kernel32 = ctypes.windll.kernel32

# region: Prototypes/Headers
HRESULT = wintypes.LONG
HPCON = wintypes.HANDLE
# Define PPROC_THREAD_ATTRIBUTE_LIST as a pointer to void (opaque type)
LPPROC_THREAD_ATTRIBUTE_LIST = wintypes.LPVOID

HANDLE_FLAG_INHERIT=0x00000001
S_OK = 0
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
PSEUDOCONSOLE_INHERIT_CURSOR = 1
STARTF_USESTDHANDLES=0x00000100 # Use standard handles
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_NO_WINDOW = 0x08000000
FORMAT_MESSAGE_ALLOCATE_BUFFER = 0x00000100
FORMAT_MESSAGE_FROM_SYSTEM = 0x00001000
FORMAT_MESSAGE_IGNORE_INSERTS=0x00000200
STILL_ACTIVE=259
WAIT_TIMEOUT=0x00000102
WAIT_OBJECT_0=0x00000000
STD_INPUT_HANDLE=-10
STD_OUTPUT_HANDLE=-11
STD_ERROR_HANDLE=-12
INVALID_HANDLE_VALUE=-1
ENABLE_ECHO_INPUT=0x0004
ENABLE_LINE_INPUT=0x0002
ENABLE_PROCESSED_INPUT=0x0001
ENABLE_VIRTUAL_TERMINAL_INPUT=0x0200
ENABLE_PROCESSED_OUTPUT=0x0001
ENABLE_VIRTUAL_TERMINAL_PROCESSING=0x0004
FILE_TYPE_CHAR=0x0002 # Console object
FILE_TYPE_PIPE=0x0003
FILE_TYPE_UNKNOWN=0x0000 # Error occurred
# Input event types
KEY_EVENT = 0x0001
MOUSE_EVENT = 0x0002
WINDOW_BUFFER_SIZE_EVENT = 0x0004
MENU_EVENT = 0x0008
FOCUS_EVENT = 0x0010

# Key event flags
CAPSLOCK_ON = 0x0080
ENHANCED_KEY = 0x0100
KEY_ACTION_DOWN = 0x0000
KEY_ACTION_UP = 0x0002
SCROLLLOCK_ON = 0x0040
NUMLOCK_ON = 0x0020

# Control key states
RIGHT_ALT_PRESSED = 0x0001
LEFT_ALT_PRESSED = 0x0002
RIGHT_CTRL_PRESSED = 0x0004
LEFT_CTRL_PRESSED = 0x0008
SHIFT_PRESSED = 0x0010

CP_UTF8=65001
CP_UTF16=1200

MAX_PATH=260

class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT),
                ("Y", wintypes.SHORT)]
class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD),
               ("lpSecurityDescriptor", wintypes.LPVOID),
               ("bInheritHandle", wintypes.BOOL)]
class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]
class STARTUPINFOEX(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", STARTUPINFO),
        ("lpAttributeList", wintypes.LPVOID)
    ]
class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD)
    ]
class KEY_EVENT_RECORD(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [
            ("UnicodeChar", wintypes.WCHAR),
            ("AsciiChar", wintypes.CHAR)
        ]
    _fields_ = [
        ("bKeyDown", wintypes.BOOL),
        ("wRepeatCount", wintypes.WORD),
        ("wVirtualKeyCode", wintypes.WORD),
        ("wVirtualScanCode", wintypes.WORD),
        ("uChar", _U),  # UNION of UnicodeChar and AsciiChar
        ("dwControlKeyState", wintypes.DWORD)
    ]

class MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwMousePosition", COORD),
        ("dwButtonState", wintypes.DWORD),
        ("dwControlKeyState", wintypes.DWORD),
        ("dwEventFlags", wintypes.DWORD)
    ]

class WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwSize", COORD)
    ]

class MENU_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwCommandId", wintypes.UINT)
    ]

class FOCUS_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bSetFocus", wintypes.BOOL)
    ]

class INPUT_RECORD(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [
            ("KeyEvent", KEY_EVENT_RECORD),
            ("MouseEvent", MOUSE_EVENT_RECORD),
            ("WindowBufferSizeEvent", WINDOW_BUFFER_SIZE_RECORD),
            ("MenuEvent", MENU_EVENT_RECORD),
            ("FocusEvent", FOCUS_EVENT_RECORD)
        ]
    
    _fields_ = [
        ("EventType", wintypes.WORD),
        ("Event", _U)
    ]

kernel32.CreatePipe.argtypes = [
    ctypes.POINTER(wintypes.HANDLE),  # hReadPipe
    ctypes.POINTER(wintypes.HANDLE),  # hWritePipe
    ctypes.POINTER(SECURITY_ATTRIBUTES), # lpPipeAttributes
    wintypes.DWORD                    # nSize
]
kernel32.CreatePipe.restype = wintypes.BOOL

kernel32.SetHandleInformation.argtypes= [
    wintypes.HANDLE, # hObject
    wintypes.DWORD, # dwMask
    wintypes.DWORD, # dwFlags
]
kernel32.SetHandleInformation.restype=wintypes.BOOL

kernel32.CreatePseudoConsole.argtypes = [
    COORD, # size
    wintypes.HANDLE, # hInput
    wintypes.HANDLE, # hOutput
    wintypes.DWORD, # dwFlags
    ctypes.POINTER(wintypes.HANDLE) # phPC
]
kernel32.CreatePseudoConsole.restype = HRESULT

kernel32.ResizePseudoConsole.argtypes = [
    wintypes.HANDLE, # hPC
    COORD, # size
]
kernel32.ResizePseudoConsole.restype = HRESULT

kernel32.ClosePseudoConsole.argtypes = [wintypes.HANDLE]
kernel32.ClosePseudoConsole.restype = None

# Define function prototypes
kernel32.HeapAlloc.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_size_t]
kernel32.HeapAlloc.restype = wintypes.LPVOID

kernel32.GetProcessHeap.restype = wintypes.HANDLE

kernel32.InitializeProcThreadAttributeList.argtypes = [
    LPPROC_THREAD_ATTRIBUTE_LIST,  # lpAttributeList
    wintypes.DWORD,               # dwAttributeCount
    wintypes.DWORD,               # dwFlags
    ctypes.POINTER(ctypes.c_size_t)               # lpSize
]
kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL

kernel32.UpdateProcThreadAttribute.argtypes = [
    LPPROC_THREAD_ATTRIBUTE_LIST,  # lpAttributeList
    wintypes.DWORD,               # dwFlags
    wintypes.DWORD,               # Attribute
    wintypes.LPVOID,              # lpValue
    ctypes.c_size_t,              # cbSize
    wintypes.LPVOID,              # lpPreviousValue
    ctypes.POINTER(ctypes.c_size_t)               # lpReturnSize
]
kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL

kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR,           # lpApplicationName
    wintypes.LPWSTR,            # lpCommandLine
    wintypes.LPVOID,            # lpProcessAttributes
    wintypes.LPVOID,            # lpThreadAttributes
    wintypes.BOOL,              # bInheritHandles
    wintypes.DWORD,             # dwCreationFlags
    wintypes.LPVOID,            # lpEnvironment
    wintypes.LPCWSTR,           # lpCurrentDirectory
    ctypes.POINTER(STARTUPINFOEX),  # lpStartupInfo
    ctypes.POINTER(PROCESS_INFORMATION)    # lpProcessInformation
]
kernel32.CreateProcessW.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.FormatMessageW.argtypes = [
    wintypes.DWORD,    # dwFlags
    wintypes.LPVOID,   # lpSource
    wintypes.DWORD,    # dwMessageId
    wintypes.DWORD,    # dwLanguageId
    wintypes.LPWSTR,   # lpBuffer
    wintypes.DWORD,    # nSize
    wintypes.LPVOID    # Arguments
]
kernel32.FormatMessageW.restype = wintypes.DWORD

kernel32.PeekNamedPipe.argtypes = [
    wintypes.HANDLE,    # hNamedPipe
    wintypes.LPVOID,    # lpBuffer
    wintypes.DWORD,     # nBufferSize
    ctypes.POINTER(wintypes.DWORD),   # lpBytesRead
    ctypes.POINTER(wintypes.DWORD),   # lpTotalBytesAvail
    ctypes.POINTER(wintypes.DWORD)    # lpBytesLeftThisMessage
]
kernel32.PeekNamedPipe.restype = wintypes.BOOL

kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, # hFile
    wintypes.LPVOID, # lpBuffer
    wintypes.DWORD, # nNumberOfBytesToRead
    ctypes.POINTER(wintypes.DWORD), # lpNumberOfBytesRead
    wintypes.LPVOID # lpOverlapped
]
kernel32.ReadFile.restype=wintypes.BOOL

kernel32.WriteFile.argtypes = [
    wintypes.HANDLE, # hFile
    wintypes.LPVOID, # lpBuffer
    wintypes.DWORD, # nNumberOfBytesToWrite
    ctypes.POINTER(wintypes.LPDWORD), # lpNumberOfBytesWritten
    wintypes.LPVOID # lpOverlapped
]
kernel32.WriteFile.restype=wintypes.BOOL

kernel32.GetExitCodeProcess.argtypes=[
    wintypes.HANDLE, # hProcess
    ctypes.POINTER(wintypes.DWORD), # lpExitCode
]
kernel32.GetExitCodeProcess.restype=wintypes.BOOL

kernel32.WaitForSingleObject.argtypes=[
    wintypes.HANDLE, # hHandle
    wintypes.DWORD, # dwMilliseconds
]
kernel32.WaitForSingleObject.restype=wintypes.DWORD

kernel32.GetStdHandle.argtypes=[wintypes.DWORD] # nStdHandle
kernel32.GetStdHandle.restype=wintypes.HANDLE

kernel32.SetStdHandle.argtypes=[
    wintypes.DWORD, # nStdHandle
    wintypes.HANDLE, # hHandle
]
kernel32.SetStdHandle.restype=wintypes.BOOL

kernel32.GetConsoleMode.argtypes=[
    wintypes.HANDLE, # hConsoleHandle
    ctypes.POINTER(wintypes.DWORD), # lpMode
]
kernel32.GetConsoleMode.restype=wintypes.BOOL

kernel32.SetConsoleMode.argtypes=[
    wintypes.HANDLE, # hConsoleHandle
    wintypes.DWORD, # dwMode
]
kernel32.SetConsoleMode.restype=wintypes.BOOL

kernel32.GetFileType.argtypes=[wintypes.HANDLE] # hFile
kernel32.GetFileType.restype=wintypes.DWORD

kernel32.GetNumberOfConsoleInputEvents.argtypes=[
    wintypes.HANDLE, # hConsoleInput
    ctypes.POINTER(wintypes.DWORD), # lpcNumberOfEvents
]
kernel32.GetNumberOfConsoleInputEvents.restype=wintypes.BOOL

class INPUT_RECORD_arr(ctypes.Array):
    _length_=io.DEFAULT_BUFFER_SIZE # type: ignore
    _type_=INPUT_RECORD # type: ignore
kernel32.ReadConsoleInputW.argtypes = [
    wintypes.HANDLE,           # hConsoleInput
    ctypes.POINTER(INPUT_RECORD_arr), # lpBuffer
    wintypes.DWORD,            # nLength
    ctypes.POINTER(wintypes.DWORD)  # lpNumberOfEventsRead
]
kernel32.ReadConsoleInputW.restype = wintypes.BOOL

kernel32.WriteConsoleW.argtypes = [
    wintypes.HANDLE, # hConsoleOutput
    wintypes.LPVOID, # lpBuffer
    wintypes.DWORD, # nNumberOfCharsToWrite
    ctypes.POINTER(wintypes.DWORD), # lpNumberOfCharsWritten
    wintypes.LPVOID, # lpReserved
]
kernel32.WriteConsoleW.restype = wintypes.BOOL

kernel32.SetConsoleOutputCP.argtypes = [wintypes.UINT] # wCodePageID
kernel32.SetConsoleOutputCP.restype = wintypes.BOOL

kernel32.SetConsoleCP.argtypes = [wintypes.UINT] # wCodePageID
kernel32.SetConsoleCP.restype = wintypes.BOOL

kernel32.GetWindowsDirectoryW.argtypes=[
    wintypes.LPWSTR, # lpBuffer
    wintypes.UINT, # uSize
]
kernel32.GetWindowsDirectoryW.restype=wintypes.UINT

kernel32.LocaleNameToLCID.argtypes=[
    wintypes.LPCWSTR, # lpName
    wintypes.DWORD, # dwFlags
]
kernel32.LocaleNameToLCID.restype=wintypes.LCID
# endregion