# OpenAI-API Structured Outputs

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

Extract structured data from PDF documents using [Docling](https://github.com/docling-project/docling/) for parsing and the OpenAI API with [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) to organize information into clean databases.

![Extracted text and PDF Invoice](reports/figures/imagen_factura.jpeg)

<a target="_blank" href="https://github.com/docling-project/docling/">
    <img src="./reports/figures/docling.png" width="300"/>
</a>

## Features

- PDF to Markdown conversion using Docling
- Structured data extraction via OpenAI API with Pydantic models
- Caching system to avoid reprocessing files (SHA-256 hash)
- Excel export with multiple organized sheets
- Batch directory processing support

## Use Case: CV Extraction

The project includes a complete pipeline to extract information from curriculum vitae:

- **Candidates**: Personal data, contact info, summary
- **Experience**: Work history with dates and responsibilities
- **Education**: Academic background
- **Skills**: Technical and soft skills with proficiency level
- **Certifications**: Courses and certificates

## Installation

### Prerequisites

- Python 3.10+
- Conda (recommended) or pip
- OpenAI API Key

### Setup

```bash
# Create conda environment
make create_environment
conda activate openai-api

# Install dependencies
make requirements

# Configure API key
echo "OPENAI_API_KEY=your-api-key" > .env
```

## Usage

### CV Extraction

```bash
python notebooks/extract_cv_data.py
```

The script:
1. Searches for PDF files in the configured directory
2. Checks if they were already processed (hash cache)
3. Converts each PDF to Markdown with Docling
4. Sends content to OpenAI for structured extraction
5. Appends data to the output Excel file

### Force Reprocessing

To reprocess already processed files, modify the `force=True` parameter in the `process_pdf()` call.

## Project Structure

```
├── notebooks/                  # Extraction scripts
│   ├── extract_cv_data.py      # Main CV pipeline
│   ├── extract_cv_data.ipynb   # Notebook version
│   └── extract_invoice_data.ipynb  # Invoice extraction
├── src/                        # Support modules
│   └── config.py               # Path configuration
├── docs/                       # Documentation
│   └── TECHNICAL_DOCUMENTATION.md  # Detailed technical docs
├── reports/figures/            # Documentation images
├── Makefile                    # Task automation
├── requirements.txt            # pip dependencies
├── pyproject.toml              # Project configuration
└── setup.cfg                   # Linter configuration
```

## Documentation

For detailed technical documentation including architecture diagrams, implementation details, and code examples, see [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md).

## Development

```bash
# Format code
make format

# Check style
make lint

# Clean temporary files
make clean
```

## Main Dependencies

| Library | Purpose |
|---------|---------|
| [docling](https://github.com/docling-project/docling/) | PDF to Markdown conversion |
| [openai](https://github.com/openai/openai-python) | API client with structured outputs |
| [pydantic](https://docs.pydantic.dev/) | Data validation and schemas |
| [pandas](https://pandas.pydata.org/) | Data manipulation |
| [openpyxl](https://openpyxl.readthedocs.io/) | Excel read/write |

## Configuration

The project uses environment variables for sensitive configuration:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required) |

Create a `.env` file in the project root with the required variables.

## License

This project is licensed under the MIT License.
