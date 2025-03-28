import os
from flask import Flask, request, jsonify, send_file
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from flask_cors import CORS
import json

# Configuración de la aplicación Flask
app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

# ================= CONFIGURACIÓN =================
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", 
         "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "Report"
WORKSHEET_NAME = "Hoja 1"
EQUIPOS_WORKSHEET_NAME = "Equipos"

# Configuración de mesas
MESA_MEXICO = ["ISAEL ORELLANA", "DANIEL GUTIERREZ", "RODRIGO NUÑEZ", 
               "MARCO ARENAS", "PEDRO NAVARRETE", "JOSE PEÑA"]
MESA_GCC = ["EDUARDO VEGA", "JORDAN VALVERDE", "JORGE MARIN", 
            "JUAN HILLMANN", "JUAN JAUREGUI", "PAMELA MARTÍNEZ"]

# ================= FUNCIONES UTILITARIAS =================
def get_sheet():
    """Conecta con Google Sheets usando credenciales de entorno"""
    try:
        # Obtener credenciales desde variable de entorno
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json:
            raise ValueError("No se encontraron credenciales en las variables de entorno")
            
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
    except Exception as e:
        print(f"Error de conexión: {str(e)}")
        return None

def get_equipos_data():
    """Obtiene los datos de clasificación de equipos"""
    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json:
            raise ValueError("No se encontraron credenciales en las variables de entorno")
            
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.worksheet(EQUIPOS_WORKSHEET_NAME)
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        print(f"Error al obtener datos de equipos: {str(e)}")
        return pd.DataFrame()

# ================= RUTAS DEL API =================
@app.route('/save', methods=['POST'])
def save_data():
    """Guarda los datos en la hoja de cálculo"""
    data = {
        "Numero de Serie": request.form.get('serial', '').strip(),
        "Razon Social": request.form.get('business', '').strip(),
        "CONNID": request.form.get('connid', '').strip(),
        "Codigo": request.form.get('code', '').split(" ")[0],
        "Codigo Herramienta": request.form.get('tool_code', ''),
        "¿Quien llama?": request.form.get('caller', ''),
        "Falla": request.form.get('falla', '').strip(),
        "Codigo CAR.": request.form.get('car_code', ''),
        "Reporte": request.form.get('report', '').strip(),
        "Agente": request.form.get('agent', ''),
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "RCA": request.form.get('rca', '')
    }
    
    # Validar campos obligatorios
    required_fields = ['Numero de Serie', 'Razon Social', 'CONNID', 'Falla', 
                      'Reporte', 'Codigo CAR.', 'Codigo', 'Codigo Herramienta', 
                      '¿Quien llama?', 'Agente']
    
    if not all(data[field] for field in required_fields):
        return jsonify({'success': False, 'message': '¡Complete todos los campos obligatorios!'})
    
    sheet = get_sheet()
    if sheet:
        try:
            sheet.append_row(list(data.values()))
            return jsonify({'success': True, 'message': 'Datos guardados correctamente'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error al guardar: {str(e)}'})
    return jsonify({'success': False, 'message': 'Error de conexión con Google Sheets'})

@app.route('/perform_search', methods=['POST'])
def perform_search():
    """Realiza búsquedas en los datos"""
    search_type = request.form.get('search_type')
    query = request.form.get('query', '').strip().lower()
    
    sheet = get_sheet()
    if not sheet:
        return jsonify({'success': False, 'data': []})
    
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    
    field_mapping = {
        "Numero de Serie": "Numero de Serie",
        "Razon Social": "Razon Social",
        "CONNID": "CONNID",
        "Falla": "Falla",
        "Codigo CAR.": "Codigo CAR.",
        "Reporte": "Reporte",
        "Agente": "Agente"
    }
    
    search_field = field_mapping.get(search_type)
    if not search_field:
        return jsonify({'success': False, 'data': []})
    
    filtered = df[df[search_field].astype(str).str.lower().str.contains(query)]
    return jsonify({'success': True, 'data': filtered.to_dict('records')})

@app.route('/perform_analysis', methods=['POST'])
def perform_analysis():
    """Realiza análisis de desempeño"""
    analysis_type = request.form.get('analysis_type')
    year = int(request.form.get('year'))
    month = request.form.get('month')
    agent = request.form.get('agent')
    mesa = request.form.get('mesa')
    
    # Obtener y filtrar datos
    sheet = get_sheet()
    df_equipos = get_equipos_data()
    
    if sheet is None or df_equipos.empty:
        return jsonify({'success': False, 'message': 'Error al obtener datos'})
    
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['RCA'] = df['RCA'].astype(str).str.upper().str.strip()
    
    # Clasificar equipos
    def clasificar_equipo(serie):
        serie = str(serie).upper()
        for _, row in df_equipos.iterrows():
            if serie.startswith(str(row['Prefijo']).upper()):
                return row['Familia']
        return 'Prod'
    
    df['TipoEquipo'] = df['Numero de Serie'].apply(clasificar_equipo)
    
    # Filtrar por fecha
    if month != "Todos":
        month_num = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(month) + 1
        df = df[(df['Fecha'].dt.year == year) & (df['Fecha'].dt.month == month_num)]
    else:
        df = df[df['Fecha'].dt.year == year]
    
    # Filtrar por agente o mesa si es necesario
    if analysis_type == "agente" and agent:
        df = df[df['Agente'] == agent]
        title = f"{agent} - {month if month != 'Todos' else f'Año {year}'}"
    elif analysis_type == "mesa" and mesa:
        def asignar_mesa(agente):
            agente = agente.upper().strip()
            if agente in [a.upper() for a in MESA_MEXICO]:
                return "México Regional"
            elif agente in [a.upper() for a in MESA_GCC]:
                return "México GCC"
            return "Desconocido"
        
        df["Mesa"] = df["Agente"].apply(asignar_mesa)
        df = df[df["Mesa"] == mesa]
        title = f"{mesa} - {month if month != 'Todos' else f'Año {year}'}"
    else:
        title = f"Todos - {month if month != 'Todos' else f'Año {year}'}"
    
    # Calcular métricas
    metricas = calcular_metricas_corregidas(df)
    
    # Generar gráfico
    img_base64 = generar_grafico(metricas, title)
    
    return jsonify({
        'success': True,
        'title': title,
        'metricas': metricas,
        'grafico': img_base64,
        'data': df.to_dict('records')
    })

@app.route('/export', methods=['POST'])
def export_data():
    """Exporta datos a Excel"""
    try:
        data = request.get_json()
        df = pd.DataFrame(data['records'])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"Reporte_{data['title']}.xlsx"
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ================= FUNCIONES DE ANÁLISIS =================
def calcular_metricas_corregidas(df):
    """Calcula métricas según las reglas especificadas"""
    try:
        df = df.copy()
        df['RCA'] = df['RCA'].astype(str).str.upper().str.strip()
        df['RCA'] = df['RCA'].replace({'SÍ': 'SI', 'Sí': 'SI', 'sí': 'SI', 'N': 'NO', 'n': 'NO'})
        
        # 1. Todos los RCA="SI" son solucionados
        todos_resueltos = df[df['RCA'] == 'SI']
        
        # 2. RCA="NO" son solucionables solo si cumplen condiciones
        no_resueltos_solucionables = df[
            (df['RCA'] == 'NO') &
            (df['TipoEquipo'].isin(['A3', 'A4'])) &
            (df['¿Quien llama?'] == 'Cliente') &
            (~df['Razon Social'].str.contains('OPERADORA OMX', case=False, na=False))
        ]
        
        total_solucionables = len(todos_resueltos) + len(no_resueltos_solucionables)
        total_resueltos = len(todos_resueltos)
        porcentaje = (total_resueltos / total_solucionables * 100) if total_solucionables > 0 else 0
        
        equipos_prod = len(df[df['TipoEquipo'] == 'Prod'])
        omx_no_resueltos = len(df[
            (df['Razon Social'].str.contains('OPERADORA OMX', case=False, na=False)) &
            (df['RCA'] == 'NO')
        ])
        
        return {
            'solucionables': total_solucionables,
            'resueltos': total_resueltos,
            'porcentaje': porcentaje,
            'equipos_prod': equipos_prod,
            'omx_no_resueltos': omx_no_resueltos
        }
    except Exception as e:
        print(f"Error en cálculo de métricas: {str(e)}")
        return {
            'solucionables': 0,
            'resueltos': 0,
            'porcentaje': 0,
            'equipos_prod': 0,
            'omx_no_resueltos': 0
        }

def generar_grafico(metricas, title):
    """Genera gráfico y lo devuelve como base64"""
    try:
        plt.style.use('seaborn-v0_8')
        fig = plt.figure(figsize=(14, 6))
        fig.suptitle(title, fontsize=14, fontweight='bold', y=1.05)
        
        # Gráfico principal
        ax1 = fig.add_subplot(121)
        labels = ['Solucionados', 'No Solucionados']
        sizes = [metricas['porcentaje'], 100 - metricas['porcentaje']]
        colors = ['#4CAF50', '#F44336']
        explode = (0.1, 0)
        
        ax1.pie(
            sizes, explode=explode, labels=labels, colors=colors,
            autopct=lambda p: f'{p:.1f}%' if p > 0 else '',
            shadow=True, startangle=90,
            wedgeprops={'linewidth': 1, 'edgecolor': 'white'},
            textprops={'fontsize': 10, 'fontweight': 'bold'}
        )
        
        ax1.set_title(
            f'% Solución\nSolucionables: {metricas["solucionables"]} | Resueltos: {metricas["resueltos"]}',
            pad=20, fontsize=12
        )
        
        # Gráfico secundario (desglose)
        ax2 = fig.add_subplot(122)
        desglose_labels = ['Solucionables', 'Resueltos', 'No Resueltos', 'Equipos Prod', 'OMX No Resueltos']
        desglose_values = [
            metricas['solucionables'],
            metricas['resueltos'],
            metricas['solucionables'] - metricas['resueltos'],
            metricas['equipos_prod'],
            metricas['omx_no_resueltos']
        ]
        colors_desglose = ['#4CAF50', '#2ECC71', '#E74C3C', '#F39C12', '#3498DB']
        
        bars = ax2.bar(desglose_labels, desglose_values, color=colors_desglose)
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')
        
        ax2.set_title('Desglose Detallado', pad=20, fontsize=12)
        ax2.set_ylabel('Cantidad de Casos')
        plt.xticks(rotation=45)
        
        # Convertir a base64
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error al generar gráfico: {str(e)}")
        return ""

if __name__ == '__main__':
    app.run(debug=True)