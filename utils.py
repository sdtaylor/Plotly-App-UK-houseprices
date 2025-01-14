import os
import json
import pandas as pd
import logging
from copy import deepcopy

import geopandas as gpd
import sqlite3

from config import config as cfg

def get_geo_data():
    """ 
    Return 2 dictionaries. One with geodata as a geopandas dataframe, another
    with the underlying data path.
    
    {'counties':gpd.GeoDataFrame, 'metros':gpd.GeoDataFrame}, ('counties':'filename','metros':'filename')
    """
    geo_data = dict()
    geo_data_paths = dict()
    for geo_type, data_file in cfg['geodata_files'].items():
        #fname = f'geodata_{region}.json'
        geo_data_paths[geo_type] = data_file

        infile = cfg['assets dir'].joinpath(data_file)
        geo_data[geo_type] = gpd.read_file(infile)

    return geo_data, geo_data_paths

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
def get_variable_info():
    return pd.read_csv(cfg['variable_info_file'])

def get_timeperiod_info():
    q = """
    SELECT * from timeperiod_info
    """
    with sqlite3.connect(cfg['data_db']) as con:
        df = pd.read_sql(q, con)
    
    return df

def get_end_dates_for_durations():
    df = get_timeperiod_info()
    
    duration_end_dates = {}
    for duration in df.duration.unique():
        # sort descending so most recent dates are 1st in drop down
        duration_end_dates[duration] =  df.query("duration==@duration").period_end.sort_values(ascending=False).tolist()

    return duration_end_dates

def get_all_region_info(return_mapping=True):
    region_info = {}

    q = """
    SELECT * FROM region_info
    """
    with sqlite3.connect(cfg['data_db']) as con:
        all_region_info = pd.read_sql(q, con)
    
    if return_mapping:
        # Make a mapping of {region_id:region_name,...}
        region_info['counties'] = all_region_info.query("region_type=='county'").set_index('region_id').to_dict()['region_name']
        region_info['metros'] = all_region_info.query("region_type=='metro'").set_index('region_id').to_dict()['region_name']
    
        return region_info
    else:
        return all_region_info
