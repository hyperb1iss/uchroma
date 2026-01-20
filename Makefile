# UChroma Development Makefile
# Run `make help` to see all available commands

DESTDIR ?=
PREFIX ?= /usr
SHELL := /bin/bash

# Use uv by default, but allow override for packaging environments
MATURIN ?= uv run maturin

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@echo -e "\033[38;2;128;255;234m━━━ UChroma Development ━━━\033[0m"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[38;2;225;53;255m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Build & Sync
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: sync
sync: ## Sync dependencies and build native extension
	uv sync --extra gtk

.PHONY: rebuild
rebuild: ## Rebuild native Rust extension (use after editing .rs files)
	$(MATURIN) develop

.PHONY: rebuild-release
rebuild-release: ## Rebuild native extension with release optimizations
	$(MATURIN) develop --release

.PHONY: build
build: ## Build wheel for distribution
	$(MATURIN) build --release

.PHONY: clean
clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ target/ wheels/
	rm -f uchroma/*.so uchroma/**/*.so
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run ruff linter
	uv run ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff linter and fix auto-fixable issues
	uv run ruff check --fix .

.PHONY: fmt
fmt: ## Format code with ruff
	uv run ruff format .

.PHONY: fmt-check
fmt-check: ## Check formatting without modifying
	uv run ruff format --check .

.PHONY: typecheck
typecheck: ## Run ty type checker
	uv run ty check uchroma/

.PHONY: tc
tc: typecheck ## Alias for typecheck

.PHONY: check
check: lint fmt-check typecheck rust-check ## Run all checks (Python + Rust)

.PHONY: fix
fix: lint-fix fmt cargo-fmt ## Fix all auto-fixable issues (Python + Rust)

.PHONY: prettier
prettier: ## Format markdown and yaml files with prettier
	npx prettier --write '**/*.md' '**/*.yaml' '**/*.yml'

.PHONY: prettier-check
prettier-check: ## Check markdown and yaml formatting
	npx prettier --check '**/*.md' '**/*.yaml' '**/*.yml'

.PHONY: clippy
clippy: ## Run Rust linter (strict)
	cargo clippy --all-targets -- -D warnings

.PHONY: cargo-fmt
cargo-fmt: ## Format Rust code
	cargo fmt

.PHONY: cargo-fmt-check
cargo-fmt-check: ## Check Rust formatting
	cargo fmt -- --check

.PHONY: rust-check
rust-check: clippy cargo-fmt-check ## Run all Rust checks (clippy + fmt)

# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: server
server: ## Run the daemon
	uv run uchromad

.PHONY: server-debug
server-debug: ## Run daemon in debug mode
	UCHROMA_LOG_LEVEL=DEBUG uv run uchromad

.PHONY: cli
cli: ## Run the CLI client (use: make cli ARGS="device list")
	uv run uchroma $(ARGS)

.PHONY: gtk
gtk: ## Run the GTK frontend
	uv run python -m uchroma.gtk

.PHONY: gtk-debug
gtk-debug: ## Run GTK frontend in debug mode
	uv run python -m uchroma.gtk -d -d -C

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run tests
	uv run pytest $(ARGS)
	cargo test --no-default-features --features auto-initialize

.PHONY: test-v
test-v: ## Run tests with verbose output
	uv run pytest -v

.PHONY: cov
cov: ## Run tests with coverage report
	uv run pytest --cov --cov-report=term-missing

.PHONY: cov-html
cov-html: ## Generate HTML coverage report
	uv run pytest --cov --cov-report=html
	@echo -e "\033[38;2;80;250;123m✓ Coverage report: htmlcov/index.html\033[0m"

.PHONY: test-rust
test-rust: ## Run Rust unit tests
	cargo test --no-default-features --features auto-initialize

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: dev
dev: ## Install dev dependencies
	uv sync --extra gtk --group dev

.PHONY: watch
watch: ## Watch for changes and rebuild (requires watchexec)
	watchexec -e py,rs -r -- make rebuild

.PHONY: info
info: ## Show package info
	@echo "Package: uchroma"
	@uv run python -c "import uchroma; print(f'Version: {uchroma.__version__}' if hasattr(uchroma, '__version__') else 'Version: unknown')"
	@echo "Python: $$(uv run python --version)"
	@uv run python -c "import uchroma; print(f'Location: {uchroma.__file__}')"

# ─────────────────────────────────────────────────────────────────────────────
# Installation (System)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: install
install: install-udev install-service install-desktop ## Install all system files (udev, systemd, desktop)
	@echo -e "\033[38;2;80;250;123m✓ Installation complete!\033[0m"
	@echo -e "\033[38;2;241;250;140m  → Run: sudo udevadm control --reload-rules\033[0m"
	@echo -e "\033[38;2;241;250;140m  → Run: systemctl --user daemon-reload\033[0m"
	@echo -e "\033[38;2;241;250;140m  → Ubuntu 24.04+: sudo make install-apparmor\033[0m"

.PHONY: install-udev
install-udev: ## Install udev rules (requires sudo)
	install -Dm644 install/udev/70-uchroma.rules $(DESTDIR)$(PREFIX)/lib/udev/rules.d/70-uchroma.rules

.PHONY: install-service
install-service: ## Install systemd user service and D-Bus activation
	install -Dm644 install/dbus/io.uchroma.service $(DESTDIR)$(PREFIX)/share/dbus-1/services/io.uchroma.service
	install -Dm644 install/systemd/uchromad.service $(DESTDIR)$(PREFIX)/lib/systemd/user/uchromad.service

.PHONY: install-desktop
install-desktop: ## Install desktop file for GTK app
	install -Dm644 install/desktop/io.uchroma.gtk.desktop $(DESTDIR)$(PREFIX)/share/applications/io.uchroma.gtk.desktop
	install -Dm644 install/icons/io.uchroma.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/io.uchroma.svg

.PHONY: install-apparmor
install-apparmor: ## Install AppArmor profile (Ubuntu 24.04+, requires sudo)
	install -Dm644 install/apparmor/usr.bin.uchromad /etc/apparmor.d/usr.bin.uchromad
	@echo -e "\033[38;2;80;250;123m✓ AppArmor profile installed\033[0m"
	@echo -e "\033[38;2;241;250;140m  → Run: sudo apparmor_parser -r /etc/apparmor.d/usr.bin.uchromad\033[0m"

.PHONY: uninstall
uninstall: uninstall-udev uninstall-service uninstall-desktop ## Uninstall all system files

.PHONY: uninstall-udev
uninstall-udev: ## Uninstall udev rules
	rm -f $(DESTDIR)$(PREFIX)/lib/udev/rules.d/70-uchroma.rules

.PHONY: uninstall-service
uninstall-service: ## Uninstall systemd service
	rm -f $(DESTDIR)$(PREFIX)/share/dbus-1/services/io.uchroma.service
	rm -f $(DESTDIR)$(PREFIX)/lib/systemd/user/uchromad.service

.PHONY: uninstall-desktop
uninstall-desktop: ## Uninstall desktop file
	rm -f $(DESTDIR)$(PREFIX)/share/applications/io.uchroma.gtk.desktop
	rm -f $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/io.uchroma.svg

.PHONY: uninstall-apparmor
uninstall-apparmor: ## Uninstall AppArmor profile
	rm -f /etc/apparmor.d/usr.bin.uchromad
	@echo -e "\033[38;2;80;250;123m✓ AppArmor profile removed\033[0m"

# ─────────────────────────────────────────────────────────────────────────────
# Debian Packaging
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: deb deb-clean deb-orig

deb: deb-clean ## Build debian package (binary only, unsigned)
	debuild -us -uc -d -b
	@echo -e "\033[38;2;80;250;123m✓ Package built: ../uchroma_*.deb\033[0m"

deb-clean: ## Clean debian build artifacts
	rm -rf debian/uchroma debian/.debhelper debian/*.debhelper debian/*.substvars debian/files target/wheels
	@echo -e "\033[38;2;80;250;123m✓ Debian build artifacts cleaned\033[0m"

deb-orig: ## Generate orig tarball from git HEAD
	git archive --format=tar.gz --prefix=uchroma-$(shell grep '^version' pyproject.toml | cut -d'"' -f2)/ HEAD > ../uchroma_$(shell grep '^version' pyproject.toml | cut -d'"' -f2).orig.tar.gz
	@echo -e "\033[38;2;80;250;123m✓ Created ../uchroma_$(shell grep '^version' pyproject.toml | cut -d'"' -f2).orig.tar.gz\033[0m"

# ─────────────────────────────────────────────────────────────────────────────
# Documentation
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: docs docs-install docs-dev docs-build docs-preview docs-lint docs-lint-fix

docs: docs-dev  ## Alias for docs-dev

docs-install:  ## Install docs dependencies
	cd docs && npm install --legacy-peer-deps

docs-dev:  ## Start docs dev server
	cd docs && npm run dev

docs-build:  ## Build docs for production
	cd docs && npm run build

docs-preview:  ## Preview production build
	cd docs && npm run preview

docs-lint:  ## Check docs formatting
	cd docs && npm run lint

docs-lint-fix:  ## Fix docs formatting
	cd docs && npm run lint:fix
