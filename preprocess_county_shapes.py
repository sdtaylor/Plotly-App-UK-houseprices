import pandas as pd
import geopandas as gpd
import json

from time import sleep
from random import random

from shapely.ops import transform

from utils import get_all_region_info

redfin_county_info = get_all_region_info(return_mapping=False).query("region_type=='county'")

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


shapes = gpd.read_file('~/data/natural_earth_counties/ne_10m_admin_2_counties_lakes.shp')

DEST_FILE = './assets/geodata_counties.json'
SIMPLIFCATION_FACTOR = 0.01
PRECISION = 2
COLUMN_LUT = {   # old->new, also signifies which to keep
    'NAME' : 'county',
    'REGION' : 'state',
    'TYPE_EN' : 'type',
    'NAME_ALT' : 'county_and_type',
    'CODE_LOCAL'   : 'fips',
    'geometry' : 'geometry',
    }


shapes = shapes[COLUMN_LUT.keys()].rename(columns=COLUMN_LUT)

shapes['geometry'] = shapes.simplify(SIMPLIFCATION_FACTOR)

shapes['geometry'] = shapes.geometry.apply(round_coordinates, ndigits=PRECISION)

shapes['name'] = shapes.apply(lambda r: f'{r.county_and_type}, {r.state}', axis=1)

#-----------------------------------------------------
# harmonize names from natural earth data with redfin names

# redfin has all Saint as St.
shapes['name'] = shapes.name.str.replace('Saint','St.')

shape_name_to_redfin_name_lut = {
    'Doña Ana County, NM' : 'Dona Ana County, NM',
    'DeBaca County, NM' : 'De Baca County, NM',
    
    'Lewis and Clark County, MT' : 'Lewis & Clark County, MT',
    'La Salle County, IL' : 'LaSalle County, IL',
    'Baltimore, MD' : 'Baltimore City County, MD', # Also a Baltimore County, which already matches between the 2 datasets
    'St. Louis City, MO' : 'St. Louis City County, MO',
    'St.e Genevieve County, MO' : 'Ste. Genevieve County, MO',
    
    'King and Queen County, VA' : 'King & Queen County, VA',
    # Some VA city-counties keep the City in redfind data,
    # Other city-counties which do *not* keep the city are address with the fix_virginia_labels function
    'Richmond City, VA' : 'Richmond City County, VA'
    }

for shape_name, redfin_name in shape_name_to_redfin_name_lut.items():
    pass
    shapes.loc[shapes.name==shape_name, 'name'] = redfin_name

def fix_virginia_labels(name):
    if ', VA' in name:
        return name.replace(' City','')
    else:
        return name
    
shapes['name'] = shapes['name'].map(fix_virginia_labels)

redfin_counties_without_shapes = redfin_county_info.query("~region_name.isin(@shapes.name)")
# Alaska has weird Borough which don't match up easily
# Virginia has a bunch of cities listed as counties since they are "independent" cities
redfin_counties_without_shapes = redfin_counties_without_shapes.query("~region_name.str.contains('AK')").query("~region_name.str.contains('VA')")

shape_json = shapes.__geo_interface__

with open(DEST_FILE,'w') as f:
    json.dump(shape_json, f, separators=(',', ':'))









