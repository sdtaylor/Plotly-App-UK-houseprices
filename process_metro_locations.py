import pandas as pd
import geopandas as gpd
import json

import geopy
from shapely.ops import transform

from utils import get_all_region_info

from tqdm import tqdm

from config import config as cfg

redfin_metro_info = get_all_region_info(return_mapping=False).query("region_type=='metro'")


    
from shapely_extra.angles import point_from_angle_and_distance
from shapely.geometry import Polygon

def star(center_point = (0,0), outer_radius=10, inner_radius=10/3, inner_radius_ratio=None):
    """ 
    Create 5 point star shape centered on center_point.
    An inner point ratio between 0.3 and 0.4 makes decent looking stars
    
    outer_radius: radius of the  outer points
    inner_radius: radius of the inner points, ignored if inner_radius_ratio is set
    inner_radius_ratio: ratio of the inner to outer radius. 
    
    """
    if inner_radius_ratio is not None:
        if inner_radius_ratio >= 1 or inner_radius_ratio <= 0:
            raise ValueError('inner_radius_ratio must be between 0-1')
        inner_radius = outer_radius * inner_radius_ratio

    #center_point = (0,0)
    #outer_radius = 5
    #inner_radius_ratio = 1/2.5
    #inner_radius = outer_radius * inner_radius_ratio
    
    # coordinates from https://math.stackexchange.com/a/3582484
    point_radi = [
        (outer_radius, 18),
        (inner_radius, 54),
        (outer_radius, 90),
        (inner_radius, 126),
        (outer_radius, 162),
        (inner_radius, 198),
        (outer_radius, 235),
        (inner_radius, 270),
        (outer_radius, 306),
        (inner_radius, 342),
        ]
    
    
    points = [
        point_from_angle_and_distance(ref_point=center_point, angle= a, distance = d, use_radians=False)
            for d, a in point_radi
        ]
    
    return Polygon(points)

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

city_gdf = gpd.read_file(point_geofile)

star_shapes = city_gdf.copy().to_crs('EPSG:3857')

star_diameter = 30 * 1000 # 30km
star_inner_ratio = 0.4

make_star = lambda g: star(center_point=g.centroid, outer_radius=star_diameter, inner_radius_ratio = star_inner_ratio)
star_shapes['geometry'] = star_shapes.geometry.apply(make_star)

star_shapes = star_shapes.to_crs('EPSG:4326')

star_shapes['geometry'] = star_shapes.geometry.apply(round_coordinates, ndigits=2)

city_json = star_shapes.__geo_interface__

dst_file = cfg['assets dir'].joinpath(cfg['geodata_files']['metros'])

with open(dst_file,'w') as f:
    json.dump(city_json, f, separators=(',', ':'))
    



