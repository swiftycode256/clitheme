# Copyright © 2023-2024 swiftycode

# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Version information definition file
"""
# spell-checker:ignore buildnumber

# Version definition file; define the package version here
# The __version__ variable must be a literal string; DO NOT use variables
__version__="2.0-dev20240930"
major=2
minor=0
release=-1 # -1 stands for "dev"
beta_release=2 # None if not beta
# For PKGBUILD
# version_main CANNOT contain hyphens (-); use underscores (_) instead
version_main="2.0_dev20240930"
version_buildnumber=1