.PHONY: e2e build clean dist tag

e2e:
	bash ./e2e.sh

build:
	python -m pip install --upgrade pip build
	python -m build

dist: clean build

clean:
	rm -rf build dist *.egg-info .eggs

# Usage: make tag VERSION=0.2.1
tag:
	@test -n "$(VERSION)" || (echo "VERSION is required, e.g. make tag VERSION=0.2.1" && exit 1)
	git tag -a v$(VERSION) -m "Release v$(VERSION)"
	@echo "Created tag v$(VERSION). Push with: git push origin v$(VERSION)"
