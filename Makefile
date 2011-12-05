all: flakes

.PHONY: flakes
flakes:
	pyflakes ./graff

.PHONY: archive
archive:
	rm -f graff.tar
	git archive --format=tar --prefix=graff/ -o graff.tar HEAD
