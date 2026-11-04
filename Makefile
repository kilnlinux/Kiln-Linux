# Kiln Linux. Run `make help`.
.PHONY: help iso test e2e run run-bios run-disk clean

help:
	@echo "make iso        build the ISO into out/ (no root needed)"
	@echo "make test       unit, integration and lint checks"
	@echo "make e2e        install the newest ISO in QEMU unattended, boot it, screenshot (needs qemu)"
	@echo "make run        boot the newest ISO in QEMU (UEFI) with a blank disk"
	@echo "make run-bios   boot the newest ISO in QEMU (legacy BIOS)"
	@echo "make run-disk   boot the installed QEMU disk (UEFI)"
	@echo "make clean      remove build/, out/ and cargo output"

iso:
	scripts/build.sh

e2e:
	tests/qemu/run.sh

test:
	scripts/test.sh

run:
	scripts/qemu.sh iso

run-bios:
	scripts/qemu.sh iso-bios

run-disk:
	scripts/qemu.sh disk

clean:
	@# The rootless work dir is owned by subordinate UIDs: delete it in a user namespace.
	if [ -d build/work ]; then unshare --map-auto --map-root-user -- rm -rf build/work; fi
	rm -rf build out
	cargo clean --manifest-path packages/kiln/Cargo.toml
