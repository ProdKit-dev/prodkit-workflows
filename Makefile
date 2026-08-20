.PHONY: check contracts actionlint

check: contracts
	python3 scripts/check_repository.py

contracts:
	python3 scripts/test_contracts.py

actionlint:
	docker run --rm -v "$$PWD:/repo:ro" --workdir /repo rhysd/actionlint:1.7.12 -color
