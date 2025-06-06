import pandas as pd
import numpy as np
import plotly.graph_objs as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

def cargar_parametros_desde_tabla(ruta):
    raw = pd.read_csv(ruta, sep='\t', engine='python', skiprows=0, header=0)
    columnas = raw.columns[1:]
    filas = raw.iloc[10:16]
    filas.index = filas.iloc[:, 0]
    filas = filas.iloc[:, 1:].astype(str).replace(',', '.', regex=True).astype(float)
    df = filas.T.reset_index()
    df.columns = ['Component', 'a', 'b', 'c', 'd', 'e', 'f']
    return df

def calcular_presion_vapor(T, a, b, c, d, e, f):
    lnP = a + b / (T + c) + d * np.log(T) + e * T**f
    return np.exp(lnP)

def calcular_ebullicion(P_objetivo, a, b, c, d, e, f):
    T_range = np.linspace(200, 700, 1000)
    lnP = a + b / (T_range + c) + d * np.log(T_range) + e * T_range**f
    P_calc = np.exp(lnP)
    idx = (np.abs(P_calc - P_objetivo)).argmin()
    return T_range[idx]

df = cargar_parametros_desde_tabla("parametros_antoine.txt.txt")
componentes_disponibles = df['Component'].unique()

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Curvas Antoine - Presión de Vapor y Temperatura de Ebullición"),

    html.Div([
        html.Label("Temperatura mínima (K):"),
        dcc.Slider(id='Tmin', min=200, max=400, step=10, value=250, marks={i: str(i) for i in range(200, 401, 50)}),
        html.Label("Temperatura máxima (K):"),
        dcc.Slider(id='Tmax', min=400, max=700, step=10, value=550, marks={i: str(i) for i in range(400, 701, 50)}),
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

    html.Div([
        html.Label("Presión objetivo (kPa):"),
        dcc.Slider(id='Ptarget', min=10, max=5000, step=10, value=101.325, marks={100: '1 bar', 1000: '10 bar', 5000: '50 bar'}),
        html.Label("Seleccionar componentes:"),
        dcc.Dropdown(id='componentes',
                     options=[{'label': c, 'value': c} for c in componentes_disponibles],
                     value=list(componentes_disponibles), multi=True),
        html.Label("Seleccionar par para analizar separación:"),
        dcc.Dropdown(id='par_componentes',
                     options=[{'label': f"{c1} - {c2}", 'value': f"{c1}|{c2}"} 
                              for i, c1 in enumerate(componentes_disponibles) 
                              for j, c2 in enumerate(componentes_disponibles) if i < j],
                     value=f"{componentes_disponibles[0]}|{componentes_disponibles[1]}")
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

    dcc.Graph(id='grafico_presion'),
    dcc.Graph(id='grafico_ebullicion'),
    dcc.Graph(id='grafico_diferencia'),
    dcc.Graph(id='grafico_diferencia_vs_presion')
])

@app.callback(
    [Output('grafico_presion', 'figure'),
     Output('grafico_ebullicion', 'figure'),
     Output('grafico_diferencia', 'figure'),
     Output('grafico_diferencia_vs_presion', 'figure')],
    [Input('Tmin', 'value'),
     Input('Tmax', 'value'),
     Input('Ptarget', 'value'),
     Input('componentes', 'value'),
     Input('par_componentes', 'value')]
)
def actualizar_graficos(Tmin, Tmax, Ptarget, componentes_seleccionados, par_componentes):
    T_range = np.linspace(Tmin, Tmax, 300)
    df_filtrado = df[df['Component'].isin(componentes_seleccionados)]

    fig_presion = go.Figure()
    fig_ebullicion = go.Figure()

    for _, row in df_filtrado.iterrows():
        nombre = row['Component']
        a, b, c, d, e, f = row[['a', 'b', 'c', 'd', 'e', 'f']]
        try:
            P = calcular_presion_vapor(T_range, a, b, c, d, e, f)
            fig_presion.add_trace(go.Scatter(x=T_range, y=P, mode='lines', name=nombre))
            T_eb = calcular_ebullicion(Ptarget, a, b, c, d, e, f)
            fig_ebullicion.add_trace(go.Bar(x=[nombre], y=[T_eb], name=nombre))
        except:
            continue

    fig_presion.update_layout(title="Presión de vapor vs Temperatura", xaxis_title="T (K)", yaxis_title="P (kPa)")
    fig_ebullicion.update_layout(title=f"Temperatura de ebullición a {Ptarget:.2f} kPa", xaxis_title="Componente", yaxis_title="Teb (K)")

    nombre1, nombre2 = par_componentes.split("|")
    fila1 = df[df["Component"] == nombre1].iloc[0]
    fila2 = df[df["Component"] == nombre2].iloc[0]

    T1 = calcular_ebullicion(Ptarget, fila1['a'], fila1['b'], fila1['c'], fila1['d'], fila1['e'], fila1['f'])
    T2 = calcular_ebullicion(Ptarget, fila2['a'], fila2['b'], fila2['c'], fila2['d'], fila2['e'], fila2['f'])

    fig_dif = go.Figure()
    fig_dif.add_trace(go.Bar(x=[f"{nombre2} - {nombre1}"], y=[abs(T2 - T1)]))
    fig_dif.update_layout(title=f"Diferencia de temperatura de ebullición a {Ptarget:.1f} kPa", yaxis_title="ΔT (K)")

    presiones = np.linspace(10, 5000, 200)
    diferencias = []
    for P in presiones:
        t1 = calcular_ebullicion(P, fila1['a'], fila1['b'], fila1['c'], fila1['d'], fila1['e'], fila1['f'])
        t2 = calcular_ebullicion(P, fila2['a'], fila2['b'], fila2['c'], fila2['d'], fila2['e'], fila2['f'])
        diferencias.append(abs(t2 - t1))

    fig_dif_vs_P = go.Figure()
    fig_dif_vs_P.add_trace(go.Scatter(x=presiones, y=diferencias, mode="lines"))
    fig_dif_vs_P.update_layout(title=f"Diferencia de ebullición entre {nombre1} y {nombre2} vs presión",
                               xaxis_title="Presión (kPa)", yaxis_title="ΔT (K)")

    return fig_presion, fig_ebullicion, fig_dif, fig_dif_vs_P

if __name__ == '__main__':
    app.run(debug=True)
