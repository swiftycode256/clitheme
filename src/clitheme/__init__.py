__all__=["frontend", "cli", "man", "exec"] 

# Prevent RuntimeWarning from displaying when running a submodule (e.g. "python3 -m clitheme.exec")
import warnings
warnings.simplefilter("ignore", category=RuntimeWarning)
from . import _globalvar, frontend, cli, man, exec
_globalvar.handle_set_themedef(frontend, "global") # type: ignore
del _globalvar # Don't expose this module by default