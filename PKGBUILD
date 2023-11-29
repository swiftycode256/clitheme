# Maintainer: swiftycode <3291929745@qq.com>
pkgname='clitheme'
pkgver=UNKNOWN # to be filled out by pkgver()
pkgrel=1 # to be filled out by pkgver()
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
source=("file://$PWD/repo-src.tar.gz")
noextract=()
md5sums=('SKIP')
validpgpkeys=()

pkgver(){
	cd src/clitheme
	pkgrel=$(python3 -c "from _version import version_relnumber; print(version_relnumber)")
	python3 -c "from _version import version_major; print(version_major)"
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
