.PHONY: test test-local kind-create kind-delete install clean

PYTHON := true
ENV := PYTHON=$(PYTHON)
VENV_NAME := venv
VENV := $(VENV_NAME)/bin

update-tools:
	@ echo " >> Pulling Latest Tools << "
	@ rm -rf Development-Tools
	@ git clone https://github.com/juno-fx/Development-Tools.git
	@ rm -rf .tools
	@ mv -v Development-Tools/.tools .tools
	@ rm -rf Development-Tools
	@ echo " >> Tools Updated << "

.tools/cluster.Makefile:
	@ $(MAKE) update-tools

test: .tools/cluster.Makefile
	@ $(MAKE) -f .tools/cluster.Makefile test --no-print-directory

down: .tools/cluster.Makefile
	@ $(MAKE) -f .tools/cluster.Makefile down --no-print-directory

dev: .tools/cluster.Makefile
	@ $(MAKE) -f .tools/cluster.Makefile dev --no-print-directory

dependencies:
	@ # This target must exist for Development-Tools to work.

lint: .tools/dev.Makefile
	@ $(VENV)/ruff check orionpy --fix --preview

format: .tools/dev.Makefile
	@ $(VENV)/ruff format orionpy --preview
	@ $(VENV)/ty check

check: .tools/dev.Makefile
	@ echo " >> Running Format Check... << "
	@ $(VENV)/ruff format orionpy --preview --check
	@ echo
	@ echo " >> Running Lint Check... << "
	@ $(VENV)/ruff check orionpy --preview
	@ $(VENV)/ty check --no-progress

install: .tools/dev.Makefile
	@ $(MAKE) -f .tools/dev.Makefile install $(ENV) --no-print-directory
