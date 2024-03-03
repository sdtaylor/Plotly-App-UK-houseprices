import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd
import sqlite3
from tqdm import tqdm

from config import config as cfg
from config import logging_config

from utils import get_variable_info

from pathlib import Path
from itertools import takewhile, repeat, product

import logging
logging.basicConfig(filename=logging_config['log_file'], **logging_config['format_args'])

def linecount(filename):
    # Line count on a text file. Efficient for larger than mem files.
    # from https://stackoverflow.com/a/27518377
    f = open(filename, 'rb')
    bufgen = takewhile(lambda x: x, (f.raw.read(1024*1024) for _ in repeat(None)))
    return sum(buf.count(b'\n') for buf in bufgen)


def expand_grid(dictionary):
   return pd.DataFrame([row for row in product(*dictionary.values())], 
                       columns=dictionary.keys())

import shutil
import requests

def download_file(url, local_path = None):
    """ 
    Download a file.
    
    If local_path is none the file is downloaded to the current directory.
    If a folder the file is downloaded there with the same filename as the url.
    If a file the file is downloaded to that name. 
    
    Returns the downloaded file path
    """
    if local_path is None:
        local_path = '.'
        
    local_path = Path(local_path)
    if local_path.is_file():
        pass
    elif local_path.is_dir():
        pass
        local_filename = url.split('/')[-1]
        local_path = local_path.joinpath(local_filename)
        
    #path = os.path.join("/{}/{}".format(folder_name, local_filename))
    with requests.get(url, stream=True) as r:
        with open(local_path, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return local_path

import hashlib

MB = 1024**2

def getmd5(filepath):
    md5 = hashlib.md5()
    
    with open(filepath, 'rb') as fo:
        while True:
            data = fo.read(2*MB)
            if not data:
                break
            md5.update(data)
    return md5.digest()

if __name__ == "__main__":

    logging.info('------------BEGIN redfin data ingest---------------')
    
    file_log = pd.read_csv(cfg['redfin_file_log'])
    current_file_info = file_log.query('current_source').iloc[0]
    
    new_raw_data_file = cfg['redfin_data_dir'].joinpath('temp.tsv')
    
    logging.info('downloading latest file')
    download_file( cfg['redfin_data_url'], local_path = new_raw_data_file)
    
    # Check the md5 against the most recent one, only update if new
    newfile_md5 = getmd5(new_raw_data_file).hex()
    if newfile_md5 == current_file_info.md5sum:
        logging.info('latest file matches md5 of older file. quitting')
        new_raw_data_file.unlink()
        exit()
    
    logging.info('new file has new md5. continuing ingest')
    temp_sqlite_file = cfg['data_db'].parent.joinpath('temp.sqlite')
    
    # Take the hard to read giant tsv file and put into an sqlite db
    read_chunksize = 10000
    n_lines = linecount(new_raw_data_file)
    n_chunks = int((n_lines/read_chunksize) + 1)
    
    logging.info(f'writing weekly_data_raw table with {n_lines} rows')
    
    with sqlite3.connect(temp_sqlite_file) as con:
        with pd.read_csv(new_raw_data_file, sep='\t', chunksize=read_chunksize) as reader:
            for file_chunk in tqdm(reader, total=n_chunks):
                pass
                #file_chunk['period_begin'] = pd.to_datetime(file_chunk['period_begin']).dt.to_pydatetime()
                #file_chunk['period_end'] = pd.to_datetime(file_chunk['period_end']).dt.to_pydatetime()
                file_chunk.to_sql('weekly_data_raw', con, if_exists='append')
                
    logging.info('creating indexes')
    with sqlite3.connect(temp_sqlite_file) as con:
        # index for get_all_data_for_timeperiod_and_var, which retrieves data for the map. 
        con.execute('create index date_duration_idx on weekly_data_raw (period_end, duration);')
        # index for get_all_data_for_region_and_var, which retrieves data for the timeseries plot
        con.execute('create index region_id_idx on weekly_data_raw (region_id, duration);')
        
    # table timperiod_info for get_timeperiod_info function
    with sqlite3.connect(temp_sqlite_file) as con:
        con.execute('drop table if exists timeperiod_info;')
        q = """
        create table timeperiod_info as
        SELECT DISTINCT period_begin, period_end, duration 
        FROM weekly_data_raw
        """
        con.execute(q)
    
    # table region_info for get_all_region_info function
    with sqlite3.connect(temp_sqlite_file) as con:
        con.execute('drop table if exists region_info;')
        q = """
        create table region_info as
        SELECT DISTINCT region_type, region_id, region_name
        FROM weekly_data_raw
        """
        con.execute(q)
    
    logging.info('testing new database file')
    
    try:
        var_info = get_variable_info()
        
        with sqlite3.connect(temp_sqlite_file) as con:
            region_info = pd.read_sql('select * from region_info', con)
            
            assert region_info['region_type'].drop_duplicates().sort_values().tolist() == ['county', 'metro'], "region_types not ['county','metro']"
            assert len(region_info) > 3000, '<3000 entries in region info'
            
            # ensure proper date formats
            period_end_dates = pd.read_sql('select distinct period_end from timeperiod_info', con).period_end
            period_end_dates = pd.to_datetime(period_end_dates)
            most_recent_period = str(period_end_dates.max().date())
            random_period = str(period_end_dates.sample(1).iloc[0].date())
            
            for variable in var_info.variable:
                for duration in ['1 weeks','4 weeks','12 weeks']:
                    for period_end in [most_recent_period, random_period]:
                        pass
                        q = f"""
                        SELECT region_id, period_end, duration, {variable}  
                        FROM weekly_data_raw 
                        WHERE period_end = '{period_end}'
                        AND duration = '{duration}';
                        """
                        df = pd.read_sql(q, con)
                        assert len(df) == 0, f'query returned no data: {variable} {period_end} {duration}'
    except Exception as e:
        logging.error(f'Failed new database tests with error {e}')
    
    logging.info('testing passed. implementing new database file')
    # TODO: clear old tsv files and sqlite files
    
    primary_filename = cfg['data_db']
    today = str(pd.Timestamp.now().date())
    
    # shuffle old and new database files
    archive_filename = primary_filename.stem + f'_archive_{today}.sqlite'
    archive_filepath = primary_filename.parent.joinpath(archive_filename)
    
    # current sqlite becomes an archive 
    primary_filename.rename(archive_filepath)
    # newest sqlite created above becomes the current
    temp_sqlite_file.rename(primary_filename)
    
    # archive the new downloaded tsv file
    new_raw_data_file_perm_name = new_raw_data_file.parent.joinpath(f'redfin_weekly_data_{today}.tsv')
    new_raw_data_file.rename(new_raw_data_file_perm_name)
    
    # add new info to the log
    newfile_info = [{
        'current_source' : True,
        'date_downloaded' : today,
        'md5sum' : newfile_md5,
        'filesize_bytes' : new_raw_data_file_perm_name.stat().st_size,
        'linecount' : n_lines,
        }]
    
    file_log['current_source'] = False
    file_log = pd.concat([file_log, pd.DataFrame(newfile_info)])
    file_log.to_csv(cfg['redfin_file_log'], index=False)
    
    logging.info('------------END redfin data ingest---------------')
    # #------------------------------------------------
    # with sqlite3.connect(sqlite_file) as con:
    #     region_info = pd.read_sql_query('select distinct region_id, region_type_id, region_name, region_type from weekly_data_raw;', con)
    #     date_info   = pd.read_sql_query('select distinct period_begin, period_end, duration from weekly_data_raw;', con)
    
    
    # # Parquet files optimbes by region_id
    # for region_id in tqdm(region_info.region_id):
    #     with sqlite3.connect(sqlite_file) as con:
    #         df = pd.read_sql_query(f"select * from weekly_data_raw where region_id={region_id}", con)
    #         df.to_parquet(parquet_dir_by_region, partition_cols='region_id')
    
    # # not sure if I need the below partitioned  by date yet,
    # # for the map I may just need the most recent
    # #
    
    
    # all_dates_and_durations = expand_grid({'period_end': date_info.period_end.unique(),
    #                                       'duration'  : date_info.duration.unique()})
    
    # # speed things up for testing by only doing recent dates
    # #all_dates_and_durations = all_dates_and_durations[all_dates_and_durations.period_end.str.contains('2023|2024')]
    
    # # parquet files optimized by date (period_end) and duration
    # for date_info in tqdm(all_dates_and_durations.itertuples(), total=len(all_dates_and_durations)):
    #     pass
    #     with sqlite3.connect(sqlite_file) as con:
    #         q = """
    #         SELECT * from weekly_data_raw 
    #         WHERE period_end='{date_info.period_end}' 
    #         AND duration='{date_info.duration}'
    #         """
    #         df = pd.read_sql_query(q, con)
    #         df.to_parquet(parquet_dir_by_date, partition_cols=['period_end', 'duration'])
    





