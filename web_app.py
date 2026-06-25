from dash import Dash, html, dash_table, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
from dash_bootstrap_templates import load_figure_template
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import os

from dashboard_data_parser import *

base_dir = Path(__file__).parent
creds_audits_log_local_file_path = base_dir / 'log_files' / 'creds_audits.log'
cmd_audits_log_local_file_path = base_dir / 'log_files' / 'cmd_audits.log'

dotenv_path = Path('public.env')
load_dotenv(dotenv_path=dotenv_path)
country = os.getenv('COUNTRY')

def validate_dataframe(df, required_columns):
    if df is None or df.empty:
        return False
    return all(col in df.columns for col in required_columns)

load_figure_template(["cyborg"])
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
image = 'assets/images/honeypy-logo-white.png'

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc_css])
app.title = "SSH_HoneyPot"
app._favicon = "assets/images/honeypy-favicon.ico"

app.layout = dbc.Container([
    dcc.Interval(id='refresh-interval', interval=30_000, n_intervals=0),
    dcc.Download(id='download-creds-csv'),
    dcc.Download(id='download-cmds-csv'),

    html.Div(
        [html.Img(src=image, style={'height': '25%', 'width': '25%'})],
        style={'textAlign': 'center'},
        className='dbc'
    ),

    html.Div(
        id='last-updated',
        style={'textAlign': 'center', 'color': '#888', 'fontSize': '0.85em', 'marginBottom': '12px'}
    ),

    dbc.Row([
        dbc.Col(dcc.Graph(id='chart-ip'), width=4),
        dbc.Col(dcc.Graph(id='chart-username'), width=4),
        dbc.Col(dcc.Graph(id='chart-password'), width=4),
    ], align='center', class_name='mb-4'),

    dbc.Row([
        dbc.Col(dcc.Graph(id='chart-commands'), width=6),
        dbc.Col(dcc.Graph(id='chart-country'), width=6),
    ], align='center', class_name='mb-4'),

    dbc.Row([
        dbc.Col(
            dbc.Button("Export Credentials CSV", id='btn-export-creds', color='primary', size='sm'),
            width='auto'
        ),
        dbc.Col(
            dbc.Button("Export Commands CSV", id='btn-export-cmds', color='secondary', size='sm'),
            width='auto'
        ),
    ], class_name='mb-4 g-2'),

    html.Div([
        html.H3(
            "Intelligence Data",
            style={'textAlign': 'center', 'fontFamily': 'Consolas, sans-serif', 'fontWeight': 'bold'}
        ),
    ]),

    html.Div(id='table-container', className='dbc'),
])


def empty_figure(title=''):
    fig = px.bar(template='cyborg', title=title)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig


@app.callback(
    Output('chart-ip', 'figure'),
    Output('chart-username', 'figure'),
    Output('chart-password', 'figure'),
    Output('chart-commands', 'figure'),
    Output('chart-country', 'figure'),
    Output('table-container', 'children'),
    Output('last-updated', 'children'),
    Input('refresh-interval', 'n_intervals'),
)
def refresh_dashboard(n):
    creds_df = parse_creds_audits_log(creds_audits_log_local_file_path)
    cmd_df = parse_cmd_audits_log(cmd_audits_log_local_file_path)

    top_ip = top_10_calculator(creds_df, 'ip_address') if validate_dataframe(creds_df, ['ip_address']) else None
    top_usernames = top_10_calculator(creds_df, 'username') if validate_dataframe(creds_df, ['username']) else None
    top_passwords = top_10_calculator(creds_df, 'password') if validate_dataframe(creds_df, ['password']) else None
    top_cmds = top_10_calculator(cmd_df, 'Command') if validate_dataframe(cmd_df, ['Command']) else None

    fig_ip = px.bar(top_ip, x='ip_address', y='count', title='Top IP Addresses', template='cyborg') \
        if validate_dataframe(top_ip, ['ip_address', 'count']) else empty_figure('Top IP Addresses')
    fig_username = px.bar(top_usernames, x='username', y='count', title='Top Usernames', template='cyborg') \
        if validate_dataframe(top_usernames, ['username', 'count']) else empty_figure('Top Usernames')
    fig_password = px.bar(top_passwords, x='password', y='count', title='Top Passwords', template='cyborg') \
        if validate_dataframe(top_passwords, ['password', 'count']) else empty_figure('Top Passwords')
    fig_commands = px.bar(top_cmds, x='Command', y='count', title='Top Commands', template='cyborg') \
        if validate_dataframe(top_cmds, ['Command', 'count']) else empty_figure('Top Commands')

    # Country lookup only runs if explicitly enabled (rate-limited external API).
    if country == 'True' and validate_dataframe(creds_df, ['ip_address']):
        country_df = ip_to_country_code(creds_df)
        top_country = top_10_calculator(country_df, 'Country_Code') \
            if validate_dataframe(country_df, ['Country_Code']) else None
        fig_country = px.bar(top_country, x='Country_Code', y='count', title='Top Countries', template='cyborg') \
            if validate_dataframe(top_country, ['Country_Code', 'count']) else empty_figure('Top Countries')
    else:
        fig_country = empty_figure('Top Countries (set COUNTRY=True in public.env to enable)')

    table = html.Div([
        dbc.Row([
            dbc.Col(
                dash_table.DataTable(
                    data=creds_df.to_dict('records') if not creds_df.empty else [],
                    columns=[{"name": "IP Address", "id": "ip_address"}],
                    style_table={'width': '100%'},
                    style_cell={'textAlign': 'left', 'color': '#2a9fd6'},
                    style_header={'fontWeight': 'bold'},
                    page_size=10,
                ),
            ),
            dbc.Col(
                dash_table.DataTable(
                    data=creds_df.to_dict('records') if not creds_df.empty else [],
                    columns=[{"name": "Usernames", "id": "username"}],
                    style_table={'width': '100%'},
                    style_cell={'textAlign': 'left', 'color': '#2a9fd6'},
                    style_header={'fontWeight': 'bold'},
                    page_size=10,
                ),
            ),
            dbc.Col(
                dash_table.DataTable(
                    data=creds_df.to_dict('records') if not creds_df.empty else [],
                    columns=[{"name": "Passwords", "id": "password"}],
                    style_table={'width': '100%'},
                    style_cell={'textAlign': 'left', 'color': '#2a9fd6'},
                    style_header={'fontWeight': 'bold'},
                    page_size=10,
                ),
            ),
        ])
    ])

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    last_updated = f"Last updated: {timestamp} — auto-refreshes every 30s"

    return fig_ip, fig_username, fig_password, fig_commands, fig_country, table, last_updated


@app.callback(
    Output('download-creds-csv', 'data'),
    Input('btn-export-creds', 'n_clicks'),
    prevent_initial_call=True,
)
def export_creds_csv(n_clicks):
    creds_df = parse_creds_audits_log(creds_audits_log_local_file_path)
    return dcc.send_data_frame(creds_df.to_csv, 'ssh_honeypot_credentials.csv', index=False)


@app.callback(
    Output('download-cmds-csv', 'data'),
    Input('btn-export-cmds', 'n_clicks'),
    prevent_initial_call=True,
)
def export_cmds_csv(n_clicks):
    cmd_df = parse_cmd_audits_log(cmd_audits_log_local_file_path)
    return dcc.send_data_frame(cmd_df.to_csv, 'ssh_honeypot_commands.csv', index=False)


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0")
