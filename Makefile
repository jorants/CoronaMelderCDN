DATE = $(shell date '+%s')

all: fetch compile push

fetch:
	python3 fetch.py

compile:
	cd WebsiteGenerator; python3 gen.py

push:
	git add -A
	git commit -m "Update $(DATE)"
	git push
