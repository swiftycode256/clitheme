# Maintainer: swiftycode <3291929745@qq.com>
pkgname='clitheme'
pkgver=UNKNOWN # to be filled out by pkgver()
pkgrel=1
pkgdesc="A text theming library for command line applications"
arch=('any')
url="https://gitee.com/swiftycode/clitheme"
license=('GPL-3-or-later')
depends=('python>=3.7')
makedepends=('python-hatch' 'python-installer' 'python-wheel')
checkdepends=()
optdepends=()
provides=($pkgname)
conflicts=($pkgname 'clitheme')
replaces=()
backup=()
options=()
install=
changelog=
source=("file://$PWD/$pkgname-src.tar.gz")
noextract=()
md5sums=('SKIP')
validpgpkeys=()

pkgver(){
	cd src/clitheme
	python3 -c "from _version import __version__; print(__version__)"
}

build() {
	hatch build -t wheel
}

check() {
	test -f dist/*.whl
}

package() {
	python3 -m installer --destdir="$pkgdir" dist/*.whl
}
