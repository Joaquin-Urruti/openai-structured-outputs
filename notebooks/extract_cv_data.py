#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import pandas as pd
import openai
from openai import OpenAI, beta
import sys
import json
import pprint
from tqdm import tqdm
import hashlib
from pathlib import Path

sys.path.append(os.path.abspath(".."))
from src import config

from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
  api_key=os.getenv('OPENAI_API_KEY')
)

from docling.document_converter import DocumentConverter


# In[2]:


HASHES_FILE = ".hashes.txt"

def calculate_file_hash(file_path):
    """Generate a SHA-256 hash of the entire file contents (binary)."""
    hash_sha256 = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    
    return hash_sha256.hexdigest()

def load_existing_hashes():
    """Load previously processed hashes from file."""
    if not os.path.exists(HASHES_FILE):
        return set()
    
    with open(HASHES_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_hash(hash_value):
    """Save a new hash to the file."""
    with open(HASHES_FILE, "a") as f:
        f.write(hash_value + "\n")

def process_pdf(file_path, force=False):
    """Check if a PDF has already been processed, if not (or if forced), process and save the hash."""
    file_hash = calculate_file_hash(file_path)
    existing_hashes = load_existing_hashes()

    # print(f"Procesando: {file_path}")
    # print(f"Hash calculado: {file_hash}")
    # print(f"Hash ya existe? {file_hash in existing_hashes}")    

    if not force and file_hash in existing_hashes:
        # print(f"Skipping file {file_path}, it has already been processed.")
        return False
    else:
        print(f"Processing and saving hash for {file_path}.")
    # Aquí iría el código de procesamiento real del PDF
    save_hash(file_hash)

    return True


# In[3]:


from pydantic import BaseModel, Field
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


# In[4]:


# root_dir = config.EXTERNAL_DATA_DIR / 'cvs'
root_dir = os.path.join(os.path.expanduser('~'), 'Library', 'CloudStorage', 'OneDrive-ESPARTINAS.A', 'DocumentacionEspartina', 'INNOVACION', 'Desarrollos propios', 'Base Datos CV Capital Humano')
output_name = 'base_cv_capital_humano.xlsx'


# In[5]:


file_list = []

for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.pdf'):
            file_path = os.path.join(root, file)
            # print(file_path)
            file_list.append(file_path)

file_list = tuple(file_list)
len(file_list)


# In[6]:


query = "Eres un prolijo y laborioso data entry del sector de recursos humanos. Tu tarea es extaer muy detalladamente toda la información relevante de los curriculum vitae recibidos en formato pdf y pasarla prolijamente a una tabla excel con el formato dado. "


# In[7]:


excel_path = os.path.join(root_dir, output_name)
# Expected sheet names
expected_sheets = ['Candidatos', 'Experiencia', 'Educacion', 'Habilidades', 'Certificaciones']

# Read all available sheets
all_sheets = pd.read_excel(excel_path, sheet_name=None)
loaded_dfs = {}

# Check and load only the sheets that exist
for sheet in expected_sheets:
    if sheet in all_sheets:
        loaded_dfs[sheet] = all_sheets[sheet]
    else:
        print(f'Warning: Sheet "{sheet}" is not present in the file.')

candidatos_df = loaded_dfs.get('Candidatos')
experiencia_df = loaded_dfs.get('Experiencia')
educacion_df = loaded_dfs.get('Educacion')
habilidades_df = loaded_dfs.get('Habilidades')
certificaciones_df = loaded_dfs.get('Certificaciones')


# In[8]:


processed = []
id_cv = candidatos_df.candidato_id.max() + 1
excluded_extensions = tuple(['.png', '.xlsx', '.jpeg'])

# Initialize lists for each DataFrame
candidatos_data = []
experiencia_data = []
educacion_data = []
habilidades_data = []
certificaciones_data = []


# In[9]:


for file_path in tqdm(file_list):
    if not file_path.endswith(excluded_extensions):
        if process_pdf(file_path=file_path, force=False):
            try:
                source = file_path
                converter = DocumentConverter()
                result = converter.convert(source)
                result_text = result.document.export_to_markdown()
            except Exception as e:
                print(f'Not processed: {file_path} - error: {e}')
                continue

            try:
                response = beta.chat.completions.parse(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[
                        {
                            "role": "user",
                            "content": f"Los datos del archivo {file_path} están en formato markdown:\n{result_text}\n\nPregunta: {query}"
                        }
                    ],
                    temperature=0,
                    max_tokens=15000,
                    response_format=Curriculum,
                    top_p=1
                )

                json_content = response.choices[0].message.content
                data = json.loads(json_content)

                candidato_id = id_cv
                id_cv += 1
                nombre_completo = data['nombre_completo']
                print(f'Procesando los datos de {nombre_completo}')

                # Datos generales del candidato
                candidatos_data.append({
                    'candidato_id': candidato_id,
                    'nombre_completo': nombre_completo,
                    'correo': data['correo'],
                    'telefono': data['telefono'],
                    'resumen': data['resumen'],
                    'file_path': file_path
                })

                # Experiencia
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

                # Educación
                for edu in data.get('educacion', []):
                    educacion_data.append({
                        'candidato_id': candidato_id,
                        'nombre_completo': nombre_completo,
                        'institucion': edu['institucion'],
                        'titulo': edu['titulo'],
                        'fecha_inicio': edu['fecha_inicio'],
                        'fecha_fin': edu['fecha_fin'],
                        'detalles': ", ".join(edu['detalles']) if edu['detalles'] else None
                    })

                # Habilidades
                for hab in data.get('habilidades', []):
                    habilidades_data.append({
                        'candidato_id': candidato_id,
                        'nombre_completo': nombre_completo,
                        'nombre': hab['nombre'],
                        'nivel': hab['nivel']
                    })

                # Certificaciones
                if data.get('certificaciones'):
                    for cert in data['certificaciones']:
                        certificaciones_data.append({
                            'candidato_id': candidato_id,
                            'nombre_completo': nombre_completo,
                            'certificacion': cert
                        })

                processed.append(file_path)

            except Exception as e:
                print(f'Error processing {file_path}: {e}')


if candidatos_data:
    # Candidates
    candidatos_df_actual = pd.DataFrame(candidatos_data)
    candidatos_df_actual['zona/area'] = candidatos_df_actual['file_path'].str.split('/', expand=True)[10]
    candidatos_df_actual = candidatos_df_actual[['candidato_id', 'nombre_completo', 'zona/area', 'correo', 'telefono', 'resumen', 'file_path']]

    # Experience
    if not experiencia_data:
        experiencia_df_actual = pd.DataFrame(columns=['candidato_id', 'nombre_completo', 'empresa', 'ubicacion', 'puesto', 'anio_inicio', 'fecha_inicio', 'fecha_fin', 'responsabilidades'])
    else:
        experiencia_df_actual = pd.DataFrame(experiencia_data)
        if 'fecha_inicio' in experiencia_df_actual.columns:
            experiencia_df_actual['anio_inicio'] = experiencia_df_actual['fecha_inicio'].str.extract(r'(\d{4})')
        if 'nombre_completo' in experiencia_df_actual.columns:
            experiencia_df_actual.nombre_completo = experiencia_df_actual.nombre_completo.str.title()
        experiencia_df_actual = experiencia_df_actual[['candidato_id', 'nombre_completo', 'empresa', 'ubicacion', 'puesto', 'anio_inicio', 'fecha_inicio', 'fecha_fin', 'responsabilidades']]

    # Education
    if not educacion_data:
        educacion_df_actual = pd.DataFrame(columns=['candidato_id', 'nombre_completo', 'institucion', 'titulo', 'anio_inicio', 'fecha_inicio', 'fecha_fin', 'detalles'])
    else:
        educacion_df_actual = pd.DataFrame(educacion_data)
        if 'nombre_completo' in educacion_df_actual.columns:
            educacion_df_actual.nombre_completo = educacion_df_actual.nombre_completo.str.title()
        if 'fecha_inicio' in educacion_df_actual.columns:
            educacion_df_actual['anio_inicio'] = educacion_df_actual['fecha_inicio'].str.extract(r'(\d{4})')
        educacion_df_actual = educacion_df_actual[['candidato_id', 'nombre_completo', 'institucion', 'titulo', 'anio_inicio', 'fecha_inicio', 'fecha_fin', 'detalles']]

    # Skills
    if not habilidades_data:
        habilidades_df_actual = pd.DataFrame(columns=['candidato_id', 'nombre_completo', 'nombre', 'nivel'])
    else:
        habilidades_df_actual = pd.DataFrame(habilidades_data)
        if 'nombre_completo' in habilidades_df_actual.columns:
            habilidades_df_actual.nombre_completo = habilidades_df_actual.nombre_completo.str.title()

    # Certifications
    if not certificaciones_data:
        certificaciones_df_actual = pd.DataFrame(columns=['candidato_id', 'nombre_completo', 'certificacion'])
    else:
        certificaciones_df_actual = pd.DataFrame(certificaciones_data)
        if 'nombre_completo' in certificaciones_df_actual.columns:
            certificaciones_df_actual.nombre_completo = certificaciones_df_actual.nombre_completo.str.title()


# In[10]:


from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

if candidatos_data:    
    # Usar ExcelWriter en modo 'a' (append) para mantener el contenido existente
    with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        # Leer las hojas existentes para saber dónde empezar a escribir
        existing_data = pd.read_excel(excel_path, sheet_name=None)
        
        # Añadir los nuevos datos debajo de los existentes en cada hoja
        if not candidatos_df_actual.empty:
            start_row = len(existing_data['Candidatos']) + 1
            candidatos_df_actual.to_excel(writer, sheet_name='Candidatos', startrow=start_row, index=False, header=False)
            
        if not experiencia_df_actual.empty:
            start_row = len(existing_data['Experiencia']) + 1
            experiencia_df_actual.to_excel(writer, sheet_name='Experiencia', startrow=start_row, index=False, header=False)
            
        if not educacion_df_actual.empty:
            start_row = len(existing_data['Educacion']) + 1
            educacion_df_actual.to_excel(writer, sheet_name='Educacion', startrow=start_row, index=False, header=False)
            
        if not habilidades_df_actual.empty:
            start_row = len(existing_data['Habilidades']) + 1
            habilidades_df_actual.to_excel(writer, sheet_name='Habilidades', startrow=start_row, index=False, header=False)
            
        if not certificaciones_df_actual.empty:
            start_row = len(existing_data['Certificaciones']) + 1
            certificaciones_df_actual.to_excel(writer, sheet_name='Certificaciones', startrow=start_row, index=False, header=False)


# Volver a abrir el archivo para aplicar estilos
workbook = load_workbook(excel_path)
bold_font = Font(bold=True)

for sheet_name in workbook.sheetnames:
    sheet = workbook[sheet_name]

    # Fijar primera fila y dos primeras columnas
    sheet.freeze_panes = 'C2'  # Fila 1 y columnas A-B quedan fijas

    # Poner en negrita la primera fila
    for cell in sheet[1]:
        cell.font = bold_font

    # Ajustar ancho de columnas al contenido
    for col_idx, col in enumerate(sheet.columns, 1):
        max_length = 0
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = max_length + 2
        sheet.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

# Guardar cambios
workbook.save(excel_path)


# In[ ]:




