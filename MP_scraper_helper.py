from MP_Scraper import MP_Scraper

#with open('MountainProjectData_db_pw.ini', 'r') as content_file:
#    pw = content_file.read()
pw = 'not_used' 
   
with open('MP_api_key.ini','r') as content_file:
    api_key = content_file.read()
#api_key = 0

db_address = 'postgresql://postgres:'+pw+'@localhost/MountainProjectData'

mp_region_url = 'https://www.mountainproject.com/area/105991052/san-jacinto-mountains'

mps = MP_Scraper(mp_region_url,db_address,api_key,verbatim=False,urlopen_delay=0.0,
                 scrape_by_radius=False, gps_location=[39.109, -120.237])
mps.scrape_MP()

#mps.scrape_route_details_helper()