import logging
import random
import sys
import time
import warnings

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
from dash.dependencies import Input, Output, State
from flask_caching import Cache

import plotly.express as px

from config import config as cfg
from figures_utils import (
    get_average_price_by_year,
    get_figure,
    price_ts,
    price_volume_ts,
)
from utils import (
    get_price_volume_df,
    get_regional_data,
    get_regional_geo_data,
    get_regional_geo_sector,
    get_schools_data,
    
    get_geo_data,
    get_all_data_for_region_and_var,
    get_all_data_for_timeperiod_and_var,
    get_variable_info,
    get_all_region_info
)

warnings.filterwarnings("ignore")


logging.basicConfig(format=cfg["logging format"], level=logging.INFO)
logging.info(f"System: {sys.version}")


""" ----------------------------------------------------------------------------
 App Settings
---------------------------------------------------------------------------- """
# regions = [
#     "Greater London",
#     "South East",
#     "South West",
#     "Midlands",
#     "North England",
#     "Wales",
#     "Counties",
# ]

colors = {"background": "#1F2630", "text": "#7FDBFF"}

geo_levels = ['country','metro']


NOTES = """
    **Notes:**
    1. Property type "Other" is filtered from the house price data.
    2. School ranking (2018-2019) is the best of GCSE and A-Level rankings.
    3. GCSE ranking can be misleading - subjects like
    Classics and Latin are excluded from scoring,
    unfairly penalising some schools.

    **Other data sources:**
    - [OpenStreetMap](https://www.openstreetmap.org)
    - [Postcode regions mapping](https://www.whichlist2.com/knowledgebase/uk-postcode-map/)
    - [Postcode boundary data](https://www.opendoorlogistics.com/data/)
    from [www.opendoorlogistics.com](https://www.opendoorlogistics.com)
    - Contains Royal Mail data © Royal Mail copyright and database right 2015
    - Contains National Statistics data © Crown copyright and database right 2015
    - [School 2019 performance data](https://www.gov.uk/school-performance-tables)
    (Ranking scores: [Attainment 8 Score](https://www.locrating.com/Blog/attainment-8-and-progress-8-explained.aspx)
    for GCSE and
    [Average Point Score](https://dera.ioe.ac.uk/26476/3/16_to_18_calculating_the_average_point_scores_2015.pdf)
    for A-Level)
"""

t0 = time.time()

""" ----------------------------------------------------------------------------
Data Pre-processing
---------------------------------------------------------------------------- """
# price_volume_df = get_price_volume_df()
# regional_price_data = get_regional_data("sector_price")
# regional_percentage_delta_data = get_regional_data("sector_percentage_delta")
# regional_geo_data, regional_geo_data_paths = get_regional_geo_data()
# regional_geo_sector = get_regional_geo_sector(regional_geo_data)
# schools_top_500 = get_schools_data()

# ---------------------------------------------

# initial values:
# initial_year = max(cfg["Years"])
# initial_region = "Greater London"

# sectors = regional_price_data[initial_year][initial_region]["Sector"].values
# initial_sector = random.choice(sectors)
# initial_geo_sector = [regional_geo_sector[initial_region][initial_sector]]

empty_series = pd.DataFrame(np.full(len(cfg["Years"]), np.nan), index=cfg["Years"])
empty_series.rename(columns={0: ""}, inplace=True)


initial_variable = 'total_homes_sold'

geo_data, geo_data_paths = get_geo_data()

variable_info = get_variable_info().sort_values('variable')
var_pretty_name_lut = {v.variable:v.pretty_name for v in  variable_info.itertuples()}
# a dictionary with {region_id:region_name,} for some things
region_id_lut = get_all_region_info()
# a data.frame with the same info for other things.
region_id_df  = get_all_region_info(return_mapping=False) 

all_time_periods = get_all_data_for_region_and_var(region_ids=[2272], variable=initial_variable)

""" ----------------------------------------------------------------------------
 Dash App
---------------------------------------------------------------------------- """
# Select theme from: https://www.bootstrapcdn.com/bootswatch/

app = dash.Dash(
    __name__,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
    # external_stylesheets=[dbc.themes.DARKLY]
    external_stylesheets=[dbc.themes.SUPERHERO],
)

server = app.server  # Needed for gunicorn
cache = Cache(
    server,
    config={
        "CACHE_TYPE": "filesystem",
        "CACHE_DIR": cfg["cache dir"],
        "CACHE_THRESHOLD": cfg["cache threshold"],
    },
)
app.config.suppress_callback_exceptions = True

# --------------------------------------------------------#

app.layout = html.Div(
    id="root",
    children=[
        # Header -------------------------------------------------#
        html.Div(
            id="header",
            children=[
                html.Div(
                    [
                        html.Div(
                            [html.H1(children="USA Real Estate Metrics")],
                            style={
                                "display": "inline-block",
                                "width": "74%",
                                "padding": "10px 0px 0px 20px",  # top, right, bottom, left
                            },
                        ),
                        html.Div(
                            [html.H6(children="Created with")],
                            style={
                                "display": "inline-block",
                                "width": "10%",
                                "textAlign": "right",
                                "padding": "0px 20px 0px 0px",  # top, right, bottom, left
                            },
                        ),
                        html.Div(
                            [
                                html.A(
                                    [
                                        html.Img(
                                            src=app.get_asset_url("dash-logo.png"),
                                            style={"height": "100%", "width": "100%"},
                                        )
                                    ],
                                    href="https://plotly.com/",
                                    target="_blank",
                                )
                            ],
                            style={
                                "display": "inline-block",
                                "width": "14%",
                                "textAlign": "right",
                                "padding": "0px 10px 0px 0px",
                            },
                        ),
                    ]
                ),
            ],
        ),
        html.Div(
            [
                dcc.Markdown(
                    "Data provided by [Redfin](https://www.redfin.com/), a national real estate brokerage"
                )
            ],
            style={"padding": "5px 0px 5px 20px"},
        ),
        # Selection control -------------------------------------#
        html.Div(
            [
                html.Div(
                    [
                        dcc.Dropdown(
                            id="variable",
                            options=[{"label": v.pretty_name, "value": v.variable} for v in variable_info.itertuples()],
                            value=initial_variable,
                            clearable=False,
                            style={"color": "black"},
                        )
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "0px 5px 10px 15px",
                        "width": "20%",
                    },
                    className="one columns",
                ),
                
                html.Div(
                    [
                        dcc.Dropdown(
                            id="region_id",
                            options=[
                                {"label": r_lab, "value": r_id}
                                for r_id, r_lab in region_id_lut['counties'].items()
                            ],
                            value=[],
                            clearable=True,
                            multi=True,
                            style={"color": "black"},
                        ),
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "0px 5px 10px 0px",
                        "width": "20%",
                    },
                    className="seven columns",
                ),
                
                html.Div(
                    [
                        dcc.Dropdown(
                            id="duration",
                            options=[{"label": v, "value": v} for v in ['1 weeks']],
                            value='1 weeks',
                            clearable=False,
                            style={"color": "black"},
                        )
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "0px 5px 10px 5px",
                        "width": "10%",
                    },
                    className="one columns",
                ),
                
                html.Div(
                    [
                        dbc.Checklist(
                            id="geo_types",
                            options=[
                                {'label':'Counties', 'value':'counties'},
                                {'label':'Metro Areas', 'value':'metros'},
                            ],
                            value=["counties",'metros'],
                            inline=True,
                        )
                    ],
                    style={
                        "display": "inline-block",
                        "textAlign": "center",
                        "padding": "5px 0px 10px 10px",
                        "width": "20%",
                    },
                    className="two columns",
                ),
                
                
                html.Div(
                    [
                        dcc.Dropdown(
                            id="period_ending",
                            options=[
                                {"label": i, "value": i}
                                for i in ['2024-01-21']
                            ],
                            value="Counties",
                            clearable=False,
                            style={"color": "black"},
                        )
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "0px 5px 10px 15px",
                        "width": "10%",
                    },
                    className="one columns",
                ),
                 

            ],
            style={"padding": "5px 0px 10px 20px"},
            className="row",
        ),
        # App Container ------------------------------------------#
        html.Div(
            id="app-container",
            children=[
                # Left Column ------------------------------------#
                html.Div(
                    id="left-column",
                    children=[
                        html.Div(
                            id="choropleth-container",
                            children=[
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H5(id="choropleth-title"),
                                            ],
                                            style={
                                                "display": "inline-block",
                                                "width": "100%",
                                            },
                                            className="eight columns",
                                        ),
      
                                    ]
                                ),
                                dcc.Graph(id="choropleth"),
                            ],
                        ),
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "20px 10px 10px 40px",
                        "width": "59%",
                    },
                    className="seven columns",
                ),
                # Right Column ------------------------------------#
                html.Div(
                    id="graph-container",
                    children=[
                        html.Div(
                            [
                                dcc.Markdown('spacer text')
                            ],
                            style={"textAlign": "left"},
                        ),
                        html.Div([dcc.Graph(id="price-time-series")]),
                    ],
                    style={
                        "display": "inline-block",
                        "padding": "20px 20px 10px 10px",
                        "width": "39%",
                    },
                    className="five columns",
                ),
            ],
            className="row",
        ),
        # Notes and credits --------------------------#
        html.Div(
            [
                html.Div(
                    [dcc.Markdown(NOTES)],
                    style={
                        "textAlign": "left",
                        "padding": "0px 0px 5px 40px",
                        "width": "69%",
                    },
                    className="nine columns",
                ),
                html.Div(
                    [
                        dcc.Markdown(
                            "© 2020 Ivan Lai "
                            + "[[Blog]](https://www.ivanlai.project-ds.net/) "
                            + "[[Email]](mailto:ivanlai.uk.2020@gmail.com)"
                        )
                    ],
                    style={
                        "textAlign": "right",
                        "padding": "10px 20px 0px 0px",
                        "width": "29%",
                    },
                    className="three columns",
                ),
            ],
            className="row",
        ),
    ],
)

""" ----------------------------------------------------------------------------
 Callback functions:
 Overview:
 region, year, graph-type, school -> choropleth-title
 region, year -> postcode options
 region, year, graph-type, postcode-value, school -> choropleth
 postcode-value, property-type-checklist -> price-time-series
 choropleth-clickData, choropleth-selectedData, region, postcode-State -> postcode-value
---------------------------------------------------------------------------- """

# Update choropleth-title with year and graph-type update
@app.callback(
    Output("choropleth-title", "children"),
    [
        Input('variable', 'value'),
        Input("duration", "value"),
        Input("geo_types", "value"),
        #Input("graph-type", "value"),
        #Input("school-checklist", "value"),
    ],
)
def update_map_title(variable, duration, geo_types):
    if 'metros' in geo_types and 'counties' in geo_types:
        geo_type_text= 'Counties and Metro Areas'
    elif 'metros' in geo_types:
        geo_type_text= 'Metro Areas'
    elif 'counties' in geo_types:
        geo_type_text= 'Counties'
    else:
        geo_type_text = ''
    
    variable_text = variable_info.query('variable==@variable').iloc[0].pretty_name
    variable_text = var_pretty_name_lut.get(variable, '')
    
    return f"{variable_text} for {geo_type_text}. Using a {duration} smoothing window."

# Update region dropdown options with either county or metro selections
@app.callback(
    Output("region_id", "options"), 
    [
     Input("geo_types", "value"), 
     #Input("year", "value")
     ]
)
def update_region_entries(geo_types):
    region_list = []
    for gtype in geo_types:
        region_list.extend(
            {"label": r_lab, "value": r_id}
            for r_id, r_lab in region_id_lut[gtype].items()
            )
    #TODO: sort alphabetical here
    return region_list



# Update choropleth-graph with year, region, graph-type update & sectors
@app.callback(
    Output("choropleth", "figure"),
    [
        Input('variable','value'),
        Input("geo_types", "value"), 
        Input("duration", "value"),
        Input("region_id", "value"),
             
      #  Input("year", "value"),
      #  Input("region", "value"),
      #  Input("graph-type", "value"),
      #  Input("postcode", "value"),
      #  Input("school-checklist", "value"),
    ],
)  # @cache.memoize(timeout=cfg['timeout'])
def update_Choropleth(variable, geo_types, duration, region_ids):
    if 'metros' in geo_types and 'counties' in geo_types:
        geo_types='all'
    else:
        geo_types=geo_types[0]
    
    
    logging.info('update_choropleth: setting things up')
    #variable = initial_variable
    df = get_all_data_for_timeperiod_and_var(variable)
    #df = get_all_data_for_region_and_var(region_id=2772, variable=variable)
    # counties only

    # don't think i need to filter by region id. chlroplet map will
    # just ignore data entries w/ no map entry, I think
    #df = df[df['region_id'].isin(region_id_lut[geo_type])]
    
    df['Price'] = df[variable]
    
    df = df.merge(region_id_df[['region_id','region_name']], how='left', on='region_id')
    
    def format_hover_text(i):
        outline = '{name}\n{variable}: {value}'
        return outline.format(
            name = i.region_name,
            variable = variable,
            value = i[variable]
            )
    df['text'] = df.apply(format_hover_text, axis=1)
    
    # For high-lighting mechanism ----------------------# 
    #---------probably need to use below to highlight on map those values cliked in bar------------------
    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]

    if "geo_types" not in changed_id:
        highlighted_geoms = geo_data[geo_types].query("region_id.isin(@region_ids)").__geo_interface__
    else:
        highlighted_geoms = None

    
    fig = get_figure(
        df = df,
        geo_data = app.get_asset_url(geo_data_paths[geo_types]),
        region=geo_types,
        gtype='Price', #TODO, get rid of this. have a single val column in all data
        year=None,
        geo_sectors=highlighted_geoms,
        school=[],
        schools_top_500=None,
    )
    
    return fig
    
    # Graph type selection------------------------------#
    if gtype in ["Price", "Volume"]:
        df = regional_price_data[year][region]
    else:
        df = regional_percentage_delta_data[year][region]

  
    # Updating figure ----------------------------------#
    fig = get_figure(
        df,
        app.get_asset_url(regional_geo_data_paths[region]),
        region,
        gtype,
        year,
        highlighted_geoms,
        school,
        schools_top_500,
    )

    return fig


# # Update price-time-series with postcode updates and graph-type
@app.callback(
    Output("price-time-series", "figure"),
    [
     Input("region_id", "value"),
     Input('variable','value'),
    # Input("postcode", "value"), 
    # Input("property-type-checklist", "value")
     ],
)
@cache.memoize(timeout=cfg["timeout"])
def update_price_timeseries(region_ids, variable):

    if len(region_ids) == 0:
        return price_ts(empty_series, "Please select regions", colors)

    if len(variable) == 0:
        return price_ts(
            empty_series, "Please select a variable", colors
        )

    # --------------------------------------------------#
    df = get_all_data_for_region_and_var(region_ids = region_ids, variable=variable)
    df = df.merge(region_id_df[['region_id','region_name']], how='left', on='region_id')
    df['period_end'] = pd.to_datetime(df['period_end'])
    
    df = df.sort_values('period_end')
    
    title = var_pretty_name_lut.get(variable)
    
    labels = {
            'period_end' : '',
            'region_name' : '',
             variable : '',
        }
    
    fig = px.scatter(df, x='period_end', y=variable, color='region_name',
                     labels = labels,
                     title=title)
    fig.update_traces(mode='lines+markers')
    fig.update_xaxes(showgrid=False)
    fig.update_layout(margin={'l': 20, 'b': 30, 'r': 10, 't': 60},
                      plot_bgcolor=colors['background'],
                      paper_bgcolor=colors['background'],
                      autosize=True,
                      font_color=colors['text'])
    
    return fig
    
    
    
    
    df = price_volume_df.iloc[
        np.isin(price_volume_df.index.get_level_values("Property Type"), ptypes),
        np.isin(price_volume_df.columns.get_level_values("Sector"), sectors),
    ]
    df.reset_index(inplace=True)
    avg_price_df = get_average_price_by_year(df, sectors)

    if len(sectors) == 1:
        index = [(a, b) for (a, b) in df.columns if a != "Average Price"]
        volume_df = df[index]
        volume_df.columns = volume_df.columns.get_level_values(0)
        return price_volume_ts(avg_price_df, volume_df, sectors, colors)
    else:
        title = f"Average prices for {len(sectors)} sectors"
        return price_ts(avg_price_df, title, colors)


# ----------------------------------------------------#

# # Update postcode dropdown values with clickData, selectedData and region
# @app.callback(
#     Output("region_id", "value"),
#     [
#         Input("choropleth", "clickData"),
#         Input("choropleth", "selectedData"),
#         Input("geo_types", "value"), 
        
#         #Input("region", "value"),
#         #Input("school-checklist", "value"),
#         State("region_id", "value"),
#         State("choropleth", "clickData"),
#     ],
# )
# def update_postcode_dropdown(
#     clickData, selectedData, geo_type, region_ids, clickData_state
# ):

#     # Logic for initialisation or when Schoold sre selected
#     if dash.callback_context.triggered[0]["value"] is None:
#         return region_ids

#     changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]

#     # if len(school) > 0 or "school" in changed_id:
#     #     clickData_state = None
#     #     return []

#     # --------------------------------------------#

#     if "geo_types" in changed_id:
#         region_ids = []
#     elif "selectedData" in changed_id:
#         postcodes = [D["location"] for D in selectedData["points"][: cfg["topN"]]]
#     elif clickData is not None and "location" in clickData["points"][0]:
#         sector = clickData["points"][0]["location"]
#         if sector in postcodes:
#             postcodes.remove(sector)
#         elif len(postcodes) < cfg["topN"]:
#             postcodes.append(sector)
#     return postcodes


# ----------------------------------------------------#

app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})

logging.info(f"Data Preparation completed in {time.time()-t0 :.1f} seconds")

# ------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------#

if __name__ == "__main__":
    logging.info(sys.version)

    # If running locally in Anaconda env:
    if "conda-forge" in sys.version:
        app.run_server(debug=True)

    # If running on AWS/Pythonanywhere production
    else:
        app.run_server(port=8050, host="0.0.0.0", debug=True)

""" ----------------------------------------------------------------------------
Terminal cmd to run:
gunicorn app:server -b 0.0.0.0:8050
---------------------------------------------------------------------------- """
