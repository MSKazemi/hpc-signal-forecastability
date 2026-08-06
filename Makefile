# hpc-signal-forecastability
#
# Two reproduction paths:
#   make reproduce           from committed derived data — no raw data needed (reviewer path)
#   make reproduce-from-raw  full pipeline from the M100 ExaData monthly archives
#
# Everything runs through `uv`, so no global Python state is required.

RAW_DIR   ?= /home/mohsen/exadata/raw
AGG_DIR   ?= /home/mohsen/exadata/time_aggregated
MIN_FREE_GB ?= 30
WORKERS   ?= 4
# Concurrency is derived from this budget, not from the core count: the machine
# is shared with other workloads and an early run was OOM-killed.
MEM_BUDGET_GB ?= 12

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
#
# Stages are numbered in dependency order. Every stage that touches bulk data
# is resumable: it shards its output under data/interim and skips work already
# done, so an interrupted run is restarted rather than repeated.

.PHONY: inventory
inventory:  ## 01 Catalogue every partition of every archive (headers only, no disk cost)
	$(PY) scripts/01_inventory.py --raw-dir $(RAW_DIR)

.PHONY: extract
extract:  ## 02 Selectively extract the partitions the study needs
	$(PY) scripts/02_extract.py --raw-dir $(RAW_DIR) --min-free-gb $(MIN_FREE_GB)

.PHONY: manifest
manifest:  ## 03 Per-series census over the fixed entity panel
	$(PY) scripts/03_manifest.py --workers $(WORKERS) --memory-budget-gb $(MEM_BUDGET_GB)

.PHONY: taxonomy
taxonomy:  ## 04 Apply the a-priori signal taxonomy
	$(PY) scripts/04_taxonomy.py

.PHONY: sample
sample:  ## 05 Draw the stratified series sample
	$(PY) scripts/05_sample.py

.PHONY: features
features:  ## 06 Model-free predictability measures
	$(PY) scripts/06_features.py

.PHONY: forecast
forecast:  ## 07 Tiered forecast benchmark
	$(PY) scripts/07_forecast.py --workers $(WORKERS)

.PHONY: link
link:  ## 08 Linking analysis: skill ~ predictability
	$(PY) scripts/08_link.py

.PHONY: figures
figures:  ## 09 Regenerate every figure from committed derived data
	$(PY) scripts/09_figures.py

.PHONY: literature
literature:  ## 10 Harvest the literature (OpenAlex / arXiv / Semantic Scholar)
	$(PY) scripts/10_literature.py

# --- reproduction paths ----------------------------------------------------

.PHONY: reproduce
reproduce: link figures  ## Rebuild tables and figures from LOCAL derived data
	@echo "Rebuilt results/ from data/derived/."
	@echo "Note: derived parquet is not committed; run reproduce-from-raw on a fresh clone."

.PHONY: reproduce-from-raw
reproduce-from-raw: inventory extract manifest taxonomy sample features forecast link figures  ## Full pipeline from raw archives
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
	@# Generated figures and the built manuscript are tracked on purpose; a PDF
	@# anywhere else is almost certainly a downloaded paper, which must not be
	@# redistributed from this repository.
	@stray=$$(git ls-files '*.pdf' \
	    | grep -v -E '^(paper/paper\.pdf|paper/figures/|results/figures/)' || true); \
	 if [ -n "$$stray" ]; then \
	   echo "FAIL: PDFs tracked outside the allowed paths:"; echo "$$stray"; exit 1; fi
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
