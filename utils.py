import os
import json
import pandas as pd
import logging
from copy import deepcopy

import sqlite3

from config import config as cfg


def get_price_volume_df():
    price_volume_df = pd.read_csv(os.path.join(cfg['app_data_dir'], 'price_volume.csv'))
    price_volume_df = price_volume_df.set_index(['Year', 'Property Type', 'Sector']).unstack(level=-1)
    price_volume_df.fillna(value=0, inplace=True)
    return price_volume_df


def get_regional_data(fname):
    regiona_data = dict()
    for year in cfg['Years']:
        df = pd.read_csv(os.path.join(cfg['app_data_dir'], f'{fname}_{year}.csv'))

        tmp = dict()
        for region in cfg['plotly_config']:
            if region == 'South East': #Include Greater London in South East graph
                mask = (df.Region==region) | (df.Region=='Greater London')
            else:
                mask = (df.Region==region)
            tmp[region] = df[mask]

        regiona_data[year] = deepcopy(tmp)

    return regiona_data


def get_regional_geo_data():
    regional_geo_data = dict()
    regional_geo_data_paths = dict()
    for region in cfg['plotly_config']:
        fname = f'geodata_{region}.json'
        regional_geo_data_paths[region] = fname

        infile = os.path.join(cfg['assets dir'], fname)
        with open(infile, "r") as read_file:
            regional_geo_data[region] = json.load(read_file)

    return regional_geo_data, regional_geo_data_paths


def get_regional_geo_sector(regional_geo_data):
    regional_geo_sector = dict()
    for k, v in regional_geo_data.items():
        regional_geo_sector[k] = get_geo_sector(v)
    return regional_geo_sector


def get_geo_sector(geo_data):
    Y = dict()
    for feature in geo_data['features']:
        sector = feature['properties']['name']
        Y[sector] = feature
    return Y


def get_schools_data():
    schools_top_500 = pd.read_csv(os.path.join(cfg['app_data_dir'], f'schools_top_500.csv'))
    schools_top_500['Best Rank'] *= -1 #reverse the rankings solely for display purpose
    return schools_top_500


# local_db = duckdb.connect()

# weekly_dir_parquet_glob = "{}/**/*.parquet".format(cfg['data_dirs']['weekly_data_by_region'])

# q = f"""
# CREATE VIEW weekly_data_by_region AS
# SELECT * from read_parquet('{weekly_dir_parquet_glob}');
# """
# local_db.execute(q)

def get_all_data_for_region_and_var(region_ids, variable, duration='1 weeks'):
    region_in_str = ','.join([str(i) for i in region_ids])
    q = f"""
    SELECT region_id, period_begin, period_end, duration, {variable}  
    FROM weekly_data_raw 
    WHERE region_id in ({region_in_str})
    AND duration = '{duration}';
    """
    with sqlite3.connect(cfg['data_db']) as con:
        df = pd.read_sql(q, con)
    
    return df

LAST_PERIOD = '2024-01-21'

#TODO: make a table optimized for this. make last
def get_all_data_for_timeperiod_and_var(variable, period_end=LAST_PERIOD, duration='1 weeks'):
    """This one is for map data"""
    q = f"""
    SELECT region_id, period_end, duration, {variable}  
    FROM weekly_data_raw 
    WHERE period_end = '{period_end}'
    AND duration = '{duration}';
    """
    with sqlite3.connect(cfg['data_db']) as con:
        df = pd.read_sql(q, con)
    
    return df

#TODO: make this a mapping with pretty var names
def get_available_variables():
    table_cols_to_exclude = ['index','region_type_id','region_name','region_type',
                             'period_begin','period_end','duration','region_id',
                             'last_updated',
                             ]
    
    with sqlite3.connect(cfg['data_db']) as con:
        cols = pd.read_sql('select * from weekly_data_raw limit 1', con).columns
    
    return [c for c in cols if c not in table_cols_to_exclude]
    
    #TODO: drop this if never using duckdb   
    return ( 
        local_db
        .execute('describe weekly_data_by_region')
        .df()
        .query("~column_name.isin(@table_cols_to_exclude)")
        .column_name
        .tolist()
        )

#TODO: optimize to another table
def get_all_region_info():
    region_info = {}

    q = """
    SELECT distinct region_type, region_id, region_name
    FROM weekly_data_raw
    """
    with sqlite3.connect(cfg['data_db']) as con:
        all_region_info = pd.read_sql(q, con)
    
    # Make a mapping of {region_id:region_name,...}
    region_info['counties'] = all_region_info.query("region_type=='county'").set_index('region_id').to_dict()['region_name']
    region_info['metros'] = all_region_info.query("region_type=='metro'").set_index('region_id').to_dict()['region_name']

    return region_info

