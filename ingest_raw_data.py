import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd
import sqlite3
from tqdm import tqdm


from config import config as cfg

from pathlib import Path
from itertools import takewhile, repeat, product

def linecount(filename):
    # Line count on a text file. Efficient for larger than mem files.
    # from https://stackoverflow.com/a/27518377
    f = open(filename, 'rb')
    bufgen = takewhile(lambda x: x, (f.raw.read(1024*1024) for _ in repeat(None)))
    return sum(buf.count(b'\n') for buf in bufgen)


def expand_grid(dictionary):
   return pd.DataFrame([row for row in product(*dictionary.values())], 
                       columns=dictionary.keys())

# sqlite_file = cfg['data_db']
# parquet_dir_by_region = cfg['data_dirs']['weekly_data_by_region']
# parquet_dir_by_date = cfg['data_dirs']['weekly_data_by_date']

raw_data_file = '/home/shawn/Downloads/weekly_housing_market_data_most_recent_2024-02-25.tsv000'
sqlite_file = cfg['data_db']
# Path(parquet_dir_by_region).mkdir(exist_ok=True)
# Path(parquet_dir_by_date).mkdir(exist_ok=True)

# Take the hard to read giant tsv file and put into an sqlite db
read_chunksize = 10000
n_lines = linecount(raw_data_file)
n_chunks = int((n_lines/read_chunksize) + 1)

with sqlite3.connect(sqlite_file) as con:
    with pd.read_csv(raw_data_file, sep='\t', chunksize=read_chunksize) as reader:
        for file_chunk in tqdm(reader, total=n_chunks):
            pass
            #file_chunk['period_begin'] = pd.to_datetime(file_chunk['period_begin']).dt.to_pydatetime()
            #file_chunk['period_end'] = pd.to_datetime(file_chunk['period_end']).dt.to_pydatetime()
            file_chunk.to_sql('weekly_data_raw', con, if_exists='append')
    
with sqlite3.connect(sqlite_file) as con:
    # index for get_all_data_for_timeperiod_and_var, which retrieves data for the map. 
    con.execute('create index date_duration_idx on weekly_data_raw (period_end, duration);')
    # index for get_all_data_for_region_and_var, which retrieves data for the timeseries plot
    con.execute('create index region_id_idx on weekly_data_raw (region_id, duration);')
    
# table timperiod_info for get_timeperiod_info function
with sqlite3.connect(sqlite_file) as con:
    con.execute('drop table if exists timeperiod_info;')
    q = """
    create table timeperiod_info as
    SELECT DISTINCT period_begin, period_end, duration 
    FROM weekly_data_raw
    """
    con.execute(q)

# table region_info for get_all_region_info function
with sqlite3.connect(sqlite_file) as con:
    con.execute('drop table if exists region_info;')
    q = """
    create table region_info as
    SELECT DISTINCT region_type, region_id, region_name
    FROM weekly_data_raw
    """
    con.execute(q)

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






