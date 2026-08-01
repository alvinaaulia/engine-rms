.PHONY: differential-validation validate-differential validate package

differential-validation:
	bash ./run_all.sh

validate-differential: differential-validation

validate:
	python ./validate_artifacts.py
	cd .. && python -m unittest differential_validation.tests.test_evidence differential_validation.tests.test_artifact_validator

package:
	python ./package_artifact.py --output ./artifact_bundle
