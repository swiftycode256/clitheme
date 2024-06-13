# Maintainer: swiftycode <3291929745@qq.com>
pkgname='clitheme'
pkgver='2.0_beta1'
pkgrel=1
pkgdesc="A text theming library for command line applications"
arch=('any')
url="https://gitee.com/swiftycode/clitheme"
license=('GPL3')
depends=('python>=3.7' 'sqlite>=3' 'man-db')
makedepends=('git' 'python-setuptools' 'python-build' 'python-installer' 'python-wheel' 'gzip')
checkdepends=()
optdepends=()
provides=()
conflicts=($pkgname)
replaces=()
backup=()
options=()
install=
changelog='debian/changelog'
source=("srctmp::git+file://$PWD#branch=v1.2_dev") # REMOVE "#branch=v1.2_dev" WHEN MERGING WITH STABLE BRANCH!!
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
	python3 -m build --wheel --no-isolation
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
	echo -n "docs/clitheme-exec.1 ..."
	test ! -f docs/clitheme-exec.1 && echo "Error" && return 1
	echo "OK"
	echo -n "docs/clitheme-man.1 ..."
	test ! -f docs/clitheme-man.1 && echo "Error" && return 1
	echo "OK"
}

package() {
	cd srctmp
	python3 -m installer --destdir="$pkgdir" dist/*.whl
	# install manpage
	mkdir -p $pkgdir/usr/share/man/man1
	gzip -c docs/clitheme.1 > $pkgdir/usr/share/man/man1/clitheme.1.gz
	gzip -c docs/clitheme-exec.1 > $pkgdir/usr/share/man/man1/clitheme-exec.1.gz
	gzip -c docs/clitheme-man.1 > $pkgdir/usr/share/man/man1/clitheme-man.1.gz
}
