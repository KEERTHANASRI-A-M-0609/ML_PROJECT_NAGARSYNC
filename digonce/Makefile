.PHONY: setup data train simulate api ui test all

setup:
	pip install -r requirements.txt
	cd frontend && npm install

data:
	python -m ml.run_pipeline --phase data

train:
	python -m ml.run_pipeline --phase train

simulate:
	python -m ml.run_pipeline --phase simulate

api:
	uvicorn backend.app.main:app --reload --port 8000

ui:
	cd frontend && npm run dev

test:
	pytest tests/ backend/tests/ -v

all:
	python -m ml.run_pipeline --phase all
	cd frontend && npm run build
