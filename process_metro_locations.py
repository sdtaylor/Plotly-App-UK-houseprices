import pandas as pd
import geopandas as gpd
import json

import geopy
from shapely.ops import transform

from utils import get_all_region_info

from tqdm import tqdm

from config import config as cfg

redfin_metro_info = get_all_region_info(return_mapping=False).query("region_type=='metro'")

def round_coordinates(geom, ndigits=2):
    
   def _round_coords(x, y, z=None):
      x = round(x, ndigits)
      y = round(y, ndigits)

      if z is not None:
          z = round(x, ndigits)
          return (x,y,z)
      else:
          return (x,y)
   
   return transform(_round_coords, geom)

from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="real estate maps")

city_coords = []

for redfin_name in tqdm(redfin_metro_info['region_name']):
    pass
    try:
        location = geolocator.geocode(redfin_name.replace(' metro area',''))
        city_coords.append(dict(
            region_name = redfin_name,
            geo_name    = location.address,
            lat    = location.latitude,
            lon    = location.longitude,
            ))
    except:
        city_coords.append(dict(
            region_name = redfin_name,
            geo_name    = None,
            lat    = None,
            lon    = None,
            ))
    # do not query the nominatum api heavily.
    sleep(random() * 2)


city_coords_df = pd.DataFrame(city_coords)
n_missing = len(city_coords_df.query("lat.isnull()"))
print(f'geocoding results: {n_missing} missing entries')
city_coords_df= city_coords_df.query("~lat.isnull()")
city_geoms = gpd.points_from_xy(x=city_coords_df.lon, y=city_coords_df.lat, crs='EPSG:4326')

city_gdf = gpd.GeoDataFrame(city_coords_df[['region_name','geo_name']], geometry=city_geoms)
# bring in region id
city_gdf = city_gdf.merge(redfin_metro_info[['region_name','region_id']], how='left', on='region_name')

point_geofile = cfg['assets dir'].joinpath('original_metro_points.geojson')
city_gdf.to_file(point_geofile, driver='GeoJSON')

city_gdf['geometry'] = city_gdf.geometry.buffer(0.2)

city_gdf['geometry'] = city_gdf.geometry.apply(round_coordinates, ndigits=2)

city_json = city_gdf.__geo_interface__

dst_file = cfg['assets dir'].joinpath(cfg['geodata_files']['metros'])

with open(dst_file,'w') as f:
    json.dump(city_json, f, separators=(',', ':'))