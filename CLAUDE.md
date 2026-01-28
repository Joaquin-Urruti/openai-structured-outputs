# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python project for extracting structured data from PDF documents using Docling for document parsing and OpenAI API with structured outputs. The primary use case is extracting CV (curriculum vitae) data and organizing it into a structured Excel database.

## Development Commands

```bash
# Environment setup
make create_environment          # Create conda env named 'openai-api' with Python 3.10
conda activate openai-api
make requirements                # Install dependencies from requirements.txt

# Code quality
make format                      # Format code with black
make lint                        # Run flake8, isort, and black checks
make clean                       # Remove compiled Python files and __pycache__

# Run CV extraction
python notebooks/extract_cv_data.py
```

## Architecture

### Source Code (`src/`)
- **config.py**: Path configuration using pathlib. Defines `PROJ_ROOT`, `DATA_DIR`, `RAW_DATA_DIR`, `INTERIM_DATA_DIR`, `PROCESSED_DATA_DIR`, `MODELS_DIR`, `REPORTS_DIR`, `FIGURES_DIR`. Loads `.env` automatically.

### CV Extraction Pipeline (`notebooks/extract_cv_data.py`)
1. Walk directory tree to find PDF files
2. Check file hash against `.hashes.txt` to skip already-processed files
3. Convert PDF to markdown using Docling's `DocumentConverter`
4. Send to OpenAI API with structured output format (Pydantic models)
5. Parse response into separate data categories
6. Append to Excel file with sheets: Candidatos, Experiencia, Educacion, Habilidades, Certificaciones

### Pydantic Models (defined in extract_cv_data.py)
- `Curriculum`: Root model containing all CV data
- `Experiencia`: Work experience entries
- `Educacion`: Education entries
- `Habilidad`: Skills with optional proficiency level
- `Idioma`: Languages with optional proficiency level

## Key Dependencies

- **docling**: PDF-to-markdown conversion
- **openai**: API client with structured outputs (`beta.chat.completions.parse`)
- **pydantic**: Data validation and schema definition
- **pandas/openpyxl**: Excel file manipulation

## Code Style

- **Formatter**: Black (line length: 99)
- **Linter**: flake8 (ignores E731, E266, E501, C901, W503)
- **Import sorting**: isort (profile: black)
- **Python version**: 3.10+

## Environment Variables

Requires `OPENAI_API_KEY` in `.env` file (loaded via python-dotenv).
