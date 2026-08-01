.PHONY: differential-validation validate package

differential-validation:
	bash ./run_all.sh

validate:
	python ./validate_artifacts.py
	python -m unittest differential_validation.tests.test_evidence

package:
	python ./package_artifact.py --output ./artifact_bundle

