# Copyright © 2023-2026 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Module used for clitheme-man

- You can access clitheme-man by invoking this module directly: 'python3 -m clitheme.man'
- You can also invoke clitheme-man in scripts using the 'main' function
"""
import sys
import os
import subprocess
import shutil
import signal
import time
from . import _globalvar, _frontend_internal as frontend
from typing import List
def _labeled_print(msg: str):
    print("[clitheme-man] "+msg, file=sys.stderr)

frontend.set_domain(_globalvar.fd_domain_name)
frontend.set_appname(_globalvar.fd_app_name)
fd=frontend.FetchDescriptor(subsections="man")

def main(args: List[str]) -> int:
    """
    Invoke clitheme-man using the given command line arguments

    Note: the first item in the argument list must be the program name 
        (e.g. ['clitheme-man', <arguments>] or ['example-app', <arguments>])
    """
    if os.name=="nt":
        _labeled_print(fd.reof("win32-not-supported", "Error: Windows platform not supported"))
        return 1
    # check if "man" exists on system
    man_executable: str=shutil.which("man") # type: ignore
    if man_executable==None:
        _labeled_print(fd.reof("man-not-installed", "Error: \"man\" is not installed on this system"))
        return 1
    env=os.environ
    prev_manpath=env.get('MANPATH')
    # check if theme is set
    theme_set=True
    if not os.path.exists(f"{_globalvar.clitheme_root_data_path}/{_globalvar.generator_manpage_pathname}"):
        _labeled_print(fd.reof("no-theme-warn", "Warning: no theme set or theme does not contain manpages"))
        theme_set=False
    # set MANPATH
    if theme_set: env['MANPATH']=_globalvar.clitheme_root_data_path+"/"+_globalvar.generator_manpage_pathname
    # Only try "man" with fallback settings if content arguments are specified
    for x in range(1,len(args)):
        arg=args[x]
        # Specified '--' and contains following content arguments
        if arg=='--' and len(args)>x+1: break
        if not arg.startswith('-'): break
    else: theme_set=False
    # invoke man
    def run_process(env) -> int:
        process=subprocess.Popen([man_executable]+args[1:], env=env)
        while process.poll()==None:
            try: time.sleep(0.001)
            except KeyboardInterrupt: process.send_signal(signal.SIGINT)
        return process.poll() # type: ignore
    returncode=run_process(env)
    # Return code is negative when exited due to signal
    if returncode>0 and theme_set:
        _labeled_print(fd.reof("prev-command-fail", "Executing \"man\" with custom path failed, trying execution with normal settings"))
        env["MANPATH"]=prev_manpath if prev_manpath!=None else ''
        returncode=run_process(os.environ)
    # If return code is a signal, handle the exit code properly
    return 128+abs(returncode) if returncode<0 else returncode

def _script_main(): # for script
    return main(sys.argv)
if __name__=="__main__":
    exit(main(sys.argv))