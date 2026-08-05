# hpc-signal-forecastability
#
# Two reproduction paths:
#   make reproduce           from committed derived data — no raw data needed (reviewer path)
#   make reproduce-from-raw  full pipeline from the M100 ExaData monthly archives
#
# Everything runs through `uv`, so no global Python state is required.

RAW_DIR   ?= /home/mohsen/exadata/raw
AGG_DIR   ?= /home/mohsen/exadata/time_aggregated
MONTHS    ?= 20-04 20-11 21-08 22-06
MIN_FREE_GB ?= 30

PY := uv run python
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------

.PHONY: help
help:  ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup:  ## Create the pinned environment
	uv sync --all-extras

.PHONY: test
test:  ## Run the test suite (known-answer measures, leakage checks)
	uv run --extra dev pytest

.PHONY: lint
lint:  ## Lint and format-check
	uv run --extra dev ruff check .

# --- pipeline stages -------------------------------------------------------

.PHONY: extract
extract:  ## Selectively extract the sampled months from the raw archives
	$(PY) scripts/01_extract.py --raw-dir $(RAW_DIR) --months $(MONTHS) \
		--min-free-gb $(MIN_FREE_GB)

.PHONY: manifest
manifest:  ## Build the series census (data/derived/manifest.parquet)
	$(PY) scripts/02_manifest.py --agg-dir $(AGG_DIR)

.PHONY: taxonomy
taxonomy:  ## Apply the a-priori signal taxonomy (data/derived/taxonomy.csv)
	$(PY) scripts/03_taxonomy.py

.PHONY: features
features:  ## Compute model-free predictability measures (data/derived/features.parquet)
	$(PY) scripts/04_features.py

.PHONY: forecast
forecast:  ## Run the tiered forecast benchmark (data/derived/skill.parquet)
	$(PY) scripts/05_forecast.py

.PHONY: link
link:  ## Linking analysis: skill ~ predictability (results/tables)
	$(PY) scripts/06_link.py

.PHONY: figures
figures:  ## Regenerate every figure from committed derived data
	$(PY) scripts/07_figures.py

.PHONY: literature
literature:  ## Harvest the literature (OpenAlex / arXiv / Semantic Scholar)
	$(PY) scripts/08_literature.py

# --- reproduction paths ----------------------------------------------------

.PHONY: reproduce
reproduce: link figures  ## Reviewer path: reproduce all results from committed data
	@echo "Reproduced all tables and figures from data/derived/."

.PHONY: reproduce-from-raw
reproduce-from-raw: extract manifest taxonomy features forecast link figures  ## Full pipeline from raw archives
	@echo "Full pipeline complete."

# --- paper -----------------------------------------------------------------

.PHONY: paper
paper:  ## Build paper/paper.pdf (pdflatex + bibtex; latexmk is not installed)
	cd paper && pdflatex -interaction=nonstopmode -halt-on-error paper.tex \
		&& (bibtex paper || true) \
		&& pdflatex -interaction=nonstopmode -halt-on-error paper.tex \
		&& pdflatex -interaction=nonstopmode -halt-on-error paper.tex
	@echo "--- undefined references / citations ---"
	@grep -E "undefined (reference|citation)|LaTeX Warning: Citation" paper/paper.log || echo "none"

# --- safety gates ----------------------------------------------------------

.PHONY: check-private
check-private:  ## Assert no private material and no PDFs are tracked by git
	@n=$$(git ls-files | grep -c '^private/' || true); \
	 if [ "$$n" != "0" ]; then echo "FAIL: $$n private files tracked"; exit 1; fi
	@n=$$(git ls-files | grep -E '\.pdf$$' | grep -v -E '^paper/' | wc -l); \
	 if [ "$$n" != "0" ]; then echo "FAIL: $$n stray PDFs tracked"; exit 1; fi
	@echo "OK: no private material or stray PDFs tracked."

.PHONY: check-authorship
check-authorship:  ## Assert every commit is authored by Mohsen with no AI trailers
	@bad=$$(git log --format='%an' | sort -u | grep -v '^Mohsen Seyedkazemi Ardebili$$' || true); \
	 if [ -n "$$bad" ]; then echo "FAIL: unexpected authors: $$bad"; exit 1; fi
	@bad=$$(git log --format='%B' | grep -icE 'co-authored-by|generated with|claude|anthropic' || true); \
	 if [ "$$bad" != "0" ]; then echo "FAIL: $$bad AI attribution lines in commit messages"; exit 1; fi
	@echo "OK: authorship clean."

.PHONY: check
check: lint test check-private check-authorship  ## Run every gate
