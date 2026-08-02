.PHONY: differential-validation validate-differential clean-validate clean-validate-wsl finalize-v4-wsl validate package

differential-validation:
	bash ./run_all.sh

validate-differential: differential-validation

clean-validate:
	bash ./scripts/clean_compose.sh

clean-validate-wsl:
	bash ./scripts/clean_wsl.sh

finalize-v4-wsl:
	python ./generate_v4_clean_execution.py --run-id "$(RUN_ID)"

validate:
	python ./validate_artifacts.py
	cd .. && python -m unittest differential_validation.tests.test_evidence differential_validation.tests.test_artifact_validator differential_validation.tests.test_canonical_json

package:
	python ./package_artifact.py --output ./artifact_bundle
