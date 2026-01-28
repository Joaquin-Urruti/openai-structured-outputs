# AI-Powered Document Data Extraction System

> **Technical Documentation**
> Automated extraction of structured data from PDF documents using AI

---

## Executive Summary

| Attribute | Details |
|-----------|---------|
| **Project** | OpenAI Structured Outputs |
| **Type** | Data Extraction Pipeline |
| **Primary Use Case** | CV/Resume Processing for HR |
| **Secondary Use Case** | Invoice Data Extraction |

**Key Capabilities**:

- Automated PDF to structured data conversion
- 100% schema-compliant output via Pydantic validation
- Incremental processing with hash-based caching
- Multi-sheet Excel database generation
- Batch processing of document directories

---

## Problem Statement

### The Challenge

Organizations receive large volumes of unstructured documents (CVs, invoices, contracts) that require manual data entry into databases and spreadsheets. This process is:

- **Time-consuming**: Manual data entry for a single CV takes 10-15 minutes
- **Error-prone**: Human transcription introduces inconsistencies and typos
- **Non-scalable**: Processing hundreds of documents creates significant backlogs
- **Costly**: Dedicated data entry staff represent ongoing operational expenses

### Business Requirements

1. Extract structured information from PDF documents automatically
2. Ensure data consistency through schema validation
3. Avoid reprocessing already-processed documents
4. Output data in a format compatible with existing workflows (Excel)
5. Handle batch processing of entire directory trees

---

## Solution Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT PROCESSING PIPELINE                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│              │    │              │    │              │    │              │
│  PDF Files   │───▶│   Docling    │───▶│  OpenAI API  │───▶│    Excel     │
│  (Input)     │    │  (Parser)    │    │  (Extractor) │    │  (Output)    │
│              │    │              │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │
       │                   ▼                   ▼                   │
       │            ┌──────────────┐    ┌──────────────┐          │
       │            │   Markdown   │    │   Pydantic   │          │
       │            │   (Format)   │    │   (Schema)   │          │
       │            └──────────────┘    └──────────────┘          │
       │                                                          │
       └──────────────────────┬───────────────────────────────────┘
                              ▼
                       ┌──────────────┐
                       │ Hash Cache   │
                       │ (.hashes.txt)│
                       └──────────────┘
```

### Data Flow

```
1. DISCOVERY          2. VALIDATION         3. CONVERSION         4. EXTRACTION
   ─────────             ──────────            ──────────            ──────────

   Directory     ──▶    Check hash    ──▶    PDF → MD      ──▶    MD → JSON
   traversal            against cache        via Docling          via OpenAI


5. TRANSFORMATION     6. PERSISTENCE        7. FORMATTING
   ──────────────        ───────────           ──────────

   JSON → DataFrames ──▶ Append to    ──▶    Apply styles
   via Pandas            Excel sheets        (bold, widths)
```

---

## Technical Implementation

### 1. File Discovery & Caching System

The system implements a SHA-256 hash-based caching mechanism to avoid reprocessing documents.

```python
HASHES_FILE = ".hashes.txt"

def calculate_file_hash(file_path):
    """Generate a SHA-256 hash of the entire file contents (binary)."""
    hash_sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()

def process_pdf(file_path, force=False):
    """Check if a PDF has already been processed."""
    file_hash = calculate_file_hash(file_path)
    existing_hashes = load_existing_hashes()

    if not force and file_hash in existing_hashes:
        return False  # Skip - already processed

    save_hash(file_hash)
    return True  # Process this file
```

**Key Design Decisions**:

- **Chunked reading** (8KB): Handles large files without memory issues
- **Binary mode**: Ensures consistent hashes across platforms
- **Append-only storage**: Simple, corruption-resistant hash persistence
- **Force flag**: Allows reprocessing when needed

### 2. Document Parsing with Docling

Docling converts PDF documents to Markdown, preserving structure and content.

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(source)
result_text = result.document.export_to_markdown()
```

**Why Markdown as intermediate format?**

- Preserves document structure (headers, lists, tables)
- Plain text is optimal for LLM processing
- Reduces token count compared to raw PDF extraction
- Human-readable for debugging

### 3. Structured Data Extraction with OpenAI

The core extraction uses OpenAI's Structured Outputs feature with Pydantic schemas.

#### Data Models (CV Extraction)

```python
from pydantic import BaseModel
from typing import List, Optional

class Educacion(BaseModel):
    institucion: str
    titulo: str
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    detalles: Optional[List[str]]

class Experiencia(BaseModel):
    empresa: str
    ubicacion: Optional[str]
    puesto: str
    fecha_inicio: Optional[str]
    fecha_fin: Optional[str]
    responsabilidades: Optional[List[str]]

class Habilidad(BaseModel):
    nombre: str
    nivel: Optional[str]

class Idioma(BaseModel):
    idioma: str
    nivel: Optional[str]

class Curriculum(BaseModel):
    nombre_completo: str
    correo: str
    telefono: Optional[str]
    resumen: Optional[str]
    experiencia: List[Experiencia]
    educacion: Optional[List[Educacion]]
    habilidades: Optional[List[Habilidad]]
    idiomas: Optional[List[Idioma]]
    certificaciones: Optional[List[str]]
    referencias: Optional[List[str]]
```

#### API Call with Structured Output

```python
from openai import beta

response = beta.chat.completions.parse(
    model="gpt-4o-mini-2024-07-18",
    messages=[
        {
            "role": "user",
            "content": f"Los datos del archivo están en formato markdown:\n{result_text}\n\nPregunta: {query}"
        }
    ],
    temperature=0,          # Deterministic output
    max_tokens=15000,       # Handle long CVs
    response_format=Curriculum,  # Pydantic schema enforcement
    top_p=1
)

json_content = response.choices[0].message.content
data = json.loads(json_content)
```

**Model Configuration Rationale**:

| Parameter | Value | Reason |
|-----------|-------|--------|
| `model` | gpt-4o-mini-2024-07-18 | Cost-effective, supports structured outputs |
| `temperature` | 0 | Deterministic extraction, no creativity needed |
| `max_tokens` | 15000 | Accommodates detailed CVs with extensive history |
| `response_format` | Pydantic class | Guarantees schema compliance |

### 4. Data Transformation Pipeline

Extracted JSON is transformed into normalized DataFrames for relational storage.

```python
# Initialize collection lists
candidatos_data = []
experiencia_data = []
educacion_data = []
habilidades_data = []
certificaciones_data = []

# Flatten nested structures
for exp in data.get('experiencia', []):
    experiencia_data.append({
        'candidato_id': candidato_id,
        'nombre_completo': nombre_completo,
        'empresa': exp['empresa'],
        'ubicacion': exp['ubicacion'],
        'puesto': exp['puesto'],
        'fecha_inicio': exp['fecha_inicio'],
        'fecha_fin': exp['fecha_fin'],
        'responsabilidades': ", ".join(exp['responsabilidades']) if exp['responsabilidades'] else None
    })

# Additional transformations
experiencia_df['anio_inicio'] = experiencia_df['fecha_inicio'].str.extract(r'(\d{4})')
```

**Data Normalization Strategy**:

```
                    ┌─────────────────┐
                    │   Curriculum    │
                    │   (1 record)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Experiencia   │ │    Educacion    │ │   Habilidades   │
│   (N records)   │ │   (N records)   │ │   (N records)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                    candidato_id (FK)
```

### 5. Excel Output with Formatting

Data is persisted to a multi-sheet Excel workbook with professional formatting.

```python
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

# Append mode preserves existing data
with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
    existing_data = pd.read_excel(excel_path, sheet_name=None)

    # Append below existing rows
    start_row = len(existing_data['Candidatos']) + 1
    candidatos_df.to_excel(writer, sheet_name='Candidatos', startrow=start_row, index=False, header=False)

# Apply formatting
workbook = load_workbook(excel_path)
bold_font = Font(bold=True)

for sheet_name in workbook.sheetnames:
    sheet = workbook[sheet_name]
    sheet.freeze_panes = 'C2'  # Freeze headers and ID columns

    for cell in sheet[1]:
        cell.font = bold_font

    # Auto-fit column widths
    for col_idx, col in enumerate(sheet.columns, 1):
        max_length = max(len(str(cell.value or '')) for cell in col)
        sheet.column_dimensions[get_column_letter(col_idx)].width = max_length + 2
```

**Excel Output Structure**:

| Sheet | Primary Key | Foreign Key | Columns |
|-------|-------------|-------------|---------|
| Candidatos | candidato_id | - | nombre, zona, correo, telefono, resumen, file_path |
| Experiencia | - | candidato_id | empresa, ubicacion, puesto, fechas, responsabilidades |
| Educacion | - | candidato_id | institucion, titulo, fechas, detalles |
| Habilidades | - | candidato_id | nombre, nivel |
| Certificaciones | - | candidato_id | certificacion |

---

## Secondary Use Case: Invoice Extraction

The system also supports invoice data extraction with a different schema.

### Invoice Data Model

```python
class InvoiceItem(BaseModel):
    codigo: str
    descripcion: str
    unidad_medida: str
    cantidad: float
    precio_unitario: float
    importe: float
    remito: Optional[str] = None
    mes_servicio: Optional[str] = None

class InvoiceTax(BaseModel):
    concepto: str
    base_imponible: Optional[float] = None
    impuesto: str
    monto_impuesto: Optional[float] = None
    total: float

class Invoice(BaseModel):
    tipo: str                           # Original/Duplicado
    numero: str
    fecha: str
    cuit_emisor: str
    razon_social_cliente: str
    cuit_cliente: str
    condicion_venta: str
    items: List[InvoiceItem]
    impuestos: List[InvoiceTax]
    subtotal: float
    total: float
    cae: str
    vencimiento_cae: str
    # ... additional fields
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Runtime | Python | 3.10+ | Primary language |
| PDF Parsing | Docling | 2.24.0 | Document to Markdown conversion |
| LLM API | OpenAI | 1.59.9 | Structured data extraction |
| Data Validation | Pydantic | 2.10.5 | Schema definition and validation |
| Data Processing | Pandas | 2.2.3 | DataFrame operations |
| Excel I/O | openpyxl | 3.1.5 | Excel file manipulation |

### Supporting Libraries

| Library | Purpose |
|---------|---------|
| python-dotenv | Environment variable management |
| loguru | Structured logging |
| tqdm | Progress bar visualization |
| hashlib | SHA-256 file hashing |

### AI/ML Dependencies (Docling)

| Library | Purpose |
|---------|---------|
| torch | Deep learning runtime |
| transformers | Pre-trained models |
| easyocr | OCR for scanned documents |
| Pillow | Image processing |

---

## System Prompt Engineering

The extraction quality depends heavily on the system prompt:

```python
query = """Eres un prolijo y laborioso data entry del sector de recursos humanos.
Tu tarea es extraer muy detalladamente toda la información relevante de los
curriculum vitae recibidos en formato pdf y pasarla prolijamente a una tabla
excel con el formato dado."""
```

**Prompt Design Principles**:

1. **Role assignment**: "data entry del sector de recursos humanos" - establishes domain expertise
2. **Task clarity**: "extraer muy detalladamente" - emphasizes thoroughness
3. **Format awareness**: "formato pdf... tabla excel" - grounds the input/output context
4. **Quality emphasis**: "prolijo y laborioso" - sets expectation for careful work

---

## Error Handling Strategy

The pipeline implements defensive error handling at multiple levels:

```python
for file_path in tqdm(file_list):
    # Level 1: File filtering
    if not file_path.endswith(excluded_extensions):

        # Level 2: Cache check
        if process_pdf(file_path=file_path, force=False):

            # Level 3: Document conversion
            try:
                converter = DocumentConverter()
                result = converter.convert(source)
            except Exception as e:
                print(f'Not processed: {file_path} - error: {e}')
                continue  # Skip to next file

            # Level 4: API extraction
            try:
                response = beta.chat.completions.parse(...)
            except Exception as e:
                print(f'Error processing {file_path}: {e}')
                continue  # Skip to next file
```

**Error Categories**:

| Level | Error Type | Handling |
|-------|------------|----------|
| File I/O | Corrupt PDF, permissions | Log and skip |
| Docling | Parsing failure, unsupported format | Log and skip |
| OpenAI API | Rate limits, token overflow | Log and skip |
| Schema | Validation failure | Implicit (Pydantic raises) |

---

## Performance Considerations

### Optimization Techniques

1. **Caching**: SHA-256 hash prevents redundant API calls
2. **Batch collection**: Data accumulated in lists, single DataFrame creation
3. **Chunked file reading**: 8KB chunks for memory efficiency
4. **Append mode**: Excel overlay avoids full file rewrite

### Resource Usage

| Resource | Consumption | Notes |
|----------|-------------|-------|
| Memory | ~500MB baseline | Docling loads ML models |
| API Cost | ~$0.002/CV | gpt-4o-mini pricing |
| Processing Time | ~5-10s/document | Docling + API latency |

---

## Deployment & Configuration

### Environment Setup

```bash
# Create conda environment
make create_environment
conda activate openai-api

# Install dependencies
make requirements

# Configure API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

### Configuration via `src/config.py`

```python
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJ_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
```

---

## Future Enhancements

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| Async processing | Parallel API calls for batch jobs | High |
| Database backend | PostgreSQL/SQLite instead of Excel | Medium |
| Web interface | Upload portal with status tracking | Medium |
| Multi-language | Support for English CVs | Low |
| Validation rules | Business logic checks on extracted data | Low |

---

## Conclusion

This document extraction system demonstrates effective integration of modern AI capabilities with practical data engineering patterns. The combination of Docling's document parsing, OpenAI's structured outputs, and Pydantic's schema validation creates a robust pipeline that transforms unstructured PDFs into clean, queryable data with minimal human intervention.

**Key Achievements**:

- Fully automated PDF to structured data pipeline
- Schema-enforced output guarantees data quality
- Incremental processing via intelligent caching
- Production-ready Excel output with formatting
- Extensible architecture for new document types
