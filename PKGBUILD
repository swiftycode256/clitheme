pkgname='clitheme'
pkgver=VERSION # to be filled out by pkgver()
pkgrel=1
pkgdesc="A text theming library for command line applications"
arch=('any')
url="https://gitee.com/swiftycode/clitheme"
license=('GPL-3-or-later')
depends=('python>=3.7')
makedepends=('python-hatch' 'python-installer' 'python-wheel')
checkdepends=()
optdepends=()
provides=('clitheme')
conflicts=('clitheme')
replaces=()
backup=()
options=()
install=
changelog=
source=("file://$PWD/$pkgname-src.tar.gz") # needs refinement
noextract=()
md5sums=('SKIP')
validpgpkeys=()

pkgver(){
	cd $pkgname*/src/clitheme
	python3 -c "from _version import __version__; print(__version__)"
}

build() {
	echo $PWD
	rm $pkgname*.tar.gz # prevent conflicts
	echo $pkgname*
	cd $pkgname*
	hatch build -t wheel
}

check() {
	cd $pkgname*
	test -f dist/$pkgname*.whl
}

package() {
	cd $pkgname*
	python3 -m installer --destdir="$pkgdir" dist/*.whl
}
