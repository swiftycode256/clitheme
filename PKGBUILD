# Maintainer: swiftycode <3291929745@qq.com>
pkgname='clitheme'
pkgver=UNKNOWN # to be filled out by pkgver()
pkgrel=1 # to be filled out by pkgver()
pkgdesc="A text theming library for command line applications"
arch=('any')
url="https://gitee.com/swiftycode/clitheme"
license=('GPL-3-or-later')
depends=('python>=3.7')
makedepends=('git' 'python-hatch' 'python-installer' 'python-wheel')
checkdepends=()
optdepends=()
provides=($pkgname)
conflicts=($pkgname 'clitheme')
replaces=()
backup=()
options=()
install=
changelog=
source=("srctmp::git+file://$PWD")
noextract=()
md5sums=('SKIP')
validpgpkeys=()
# Make sure that it doesn't conflict with "src" directory
BUILDDIR="$PWD/buildtmp"
pkgver(){
	cd srctmp
	cd src/clitheme
	pkgrel=$(python3 -c "from _version import version_buildnumber; print(version_buildnumber)")
	python3 -c "from _version import version_main; print(version_main)"
}

build() {
	cd srctmp
	hatch build -t wheel
}

check() {
	cd srctmp
	echo -n "Ensuring generated wheel files exist..."
	test ! -f dist/*.whl && echo "Error" && return 1
	echo "OK"
	# manpage
	echo "Ensuring manpage files (in docs directory) exist:"
	echo -n "docs/clitheme.1 ..."
	test ! -f docs/clitheme.1 && echo "Error" && return 1
	echo "OK"
}

package() {
	cd srctmp
	python3 -m installer --destdir="$pkgdir" dist/*.whl
	# install manpage
	mkdir -p $pkgdir/usr/share/man/man1
	gzip -c docs/clitheme.1 > $pkgdir/usr/share/man/man1/clitheme.1.gz
}
