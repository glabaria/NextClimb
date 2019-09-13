from bs4 import BeautifulSoup
from urllib.request import urlopen
from configparser import ConfigParser
from IPython.core.debugger import set_trace
import sqlalchemy as db
import time
import psycopg2
import requests
import json
import pickle
import collections

class MP_Scraper(object):
    def __init__(self,
                 route_page,
                 postgre_address,
                 mp_api_key,
                 start_ind=0,
                 stop_ind=-1,
                 urlopen_delay=0.01,
                 verbatim=False,
                 initialize_db=False):
        
        page = urlopen(route_page)
        self.root_soup = BeautifulSoup(page,'html.parser')
        self.stop_ind = stop_ind
        self.start_ind = start_ind
        self.urlopen_delay = urlopen_delay
        self.verbatim = verbatim
        self.is_area_complete_dict = {}
        
        self.engine = db.create_engine(postgre_address)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.routes_table = db.Table('routes', self.metadata, autoload=True, autoload_with=self.engine)
        
        self.mp_api_key = mp_api_key
        
        self.route_id_dict = {}
        self.user_id_dict = {}
        #self.user_route_rating_dict = {}
        
        self.route_id_dict = pickle.load( open( "route_table.p", "rb" ) )
        self.user_id_dict = pickle.load( open( "user_table.p", "rb" ) )
        
        if initialize_db:
            table_ini_files = ['create_route_table.ini',
                               'create_user_table.ini',
                               'create_user_route_table.ini',
                               'create_user_ticks_table.ini',
                               'create_user_todo_table.ini']
            conn,cur = self.connect_db()
            
            for fname in table_ini_files:
                command = self.read_create_db_table_file(fname)
                self.create_db_table(conn,cur,command)
                conn.commit()
            
            cur.close()
            
            self.disconnect_db(conn)
        
    def config_db(self,filename='database_params.ini', 
                  section='postgresql'):
        parser = ConfigParser()
        parser.read(filename)
        
        #get section
        db = {}
        if parser.has_section(section):
            params = parser.items(section)
            for p in params:
                db[p[0]] = p[1]
        else:
            raise Exception('Section {0} not found in the {1} file'.format(section,filename))
            
        return db
    
    #connect to the PostgreSQL database server
    def connect_db(self):
        conn = None
        try:
            params = self.config_db()
            
            if self.verbatim:
                print('connecting to Postgre database...')
            
            conn = psycopg2.connect(**params)
                
            cur = conn.cursor()
            
            self.db_version = cur.fetchone()
            if self.verbatim:
                print(self.db_version)
                
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
            
        return conn,cur
            
    def disconnect_db(self,conn):
        if conn is not None:
            conn.close()
                    
    def read_create_db_table_file(self, filename):
        file = open(filename, mode='r')
        content = file.read()
        file.close()
        
        return content
    
    def create_db_table(self,conn,cur,command):
        try:
            cur.execute(command)
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
        
    '''
    input:
        soup: BeautifulSoup instance with html parser
        tag: html tag to find
        class_name: class name to find within tag
        id_name: id name of class
        stop_ind: routine returns first stop_ind 
        is_route_level: boolean, set to true if this level is the climbing routes
    
    returns state/region/route area/route from tag with class name class_name
    '''
    def get_route_level_data(self, soup, tag, class_name, id_name='', 
                             start_ind=0, stop_ind=-1, is_route_level=False):
        
        #set_trace()
        
        if not id_name:
            content = soup.find_all(tag,class_=class_name)
        else:
            content = soup.find_all(tag,class_=class_name,id=id_name)
        
        counter = 0
        
        if not content:
            return [None, None, None]
        
        link_list = []
        text_list = []
        for c in content:
            if is_route_level:
                #set_trace()
                routes = c.find_all('a')
                
                for r in routes:
                    if counter < start_ind:
                        continue
                    
                    if stop_ind != -1:
                        if counter > stop_ind:
                            break
                    
                    curr_route_name = r.get_text()
                    curr_route_link = r['href']
                    
                    link_list.append(curr_route_link)
                    text_list.append(curr_route_name)
            else:
                if stop_ind != -1:
                    if counter > stop_ind:
                        break
                        
                curr = c.find('a')
                curr_link = curr['href']
                curr_text = curr.get_text()
            
                link_list.append(curr_link)
                text_list.append(curr_text)
            
                counter += 1
            
        return content, link_list, text_list
        
    def get_route_level_data_helper(self, soup, start_ind=0, stop_ind=-1):
        #set_trace()
        content_area, link_area, text_area = \
            self.get_route_level_data(soup,'div','lef-nav-row',\
                                      start_ind=start_ind,stop_ind=stop_ind)
    
        content_route, link_route, text_route = \
            self.get_route_level_data(soup,'table','width100',id_name='left-nav-route-table',\
                                      is_route_level=True,start_ind=start_ind,stop_ind=stop_ind)
    
        return content_area, link_area, text_area, \
                   content_route, link_route, text_route
    
    def get_children(self,soup,start_ind=0,stop_ind=-1,is_root=False):
        if is_root:
            content_area, link_area, text_area, \
                content_route, link_route, text_rout = \
                    self.get_route_level_data_helper(soup,start_ind=start_ind,stop_ind=stop_ind)
        else:
            content_area, link_area, text_area,\
                content_route, link_route, text_route = \
                    self.get_route_level_data_helper(soup,start_ind=0,stop_ind=-1)
                    
        #set_trace()
        if link_area:
            #print(link_area)
            
            link_master = []
            text_master = []
        
            for laind in range(len(link_area)):            
                time.sleep(self.urlopen_delay)
                curr_soup = BeautifulSoup(urlopen(link_area[laind]),'html.parser')
                
                #set_trace()
                
                #if link_area == ['https://www.mountainproject.com/area/108533355/little-eastatoee']:
                #    set_trace()
                    
                [link, text] = self.get_children(curr_soup)
                link_master.append([link_area[laind], link])
                text_master.append([text_area[laind], text])
                
            return [link_master, text_master]
        
        if link_route:
            return [link_route, text_route]
        else:
            return [None,None]
        
    #extract route of area id from MP URL
    def get_id(self,link):
        sep = link.split('/')
        
        id_ = sep[-2] #id should be 2nd to last element
        try: 
            int(id_)
            return int(id_)
        except ValueError:
            return None
        
        #return int(sep[-2]) #id is always 2nd to last in this delimiter

    def scrape_MP(self):
        #[master_content, master_link, master_name] = self.find_master_area()
        
        start = time.time()
        [route_link,route_name] = self.get_children(self.root_soup)
        end = time.time()
        #set_trace()
        
        if self.verbatim:
            #print('master areas:',master_name)
            print(route_name)
            print('time elapsed = ',end-start)
            
        ids,route_links = self.get_all_route_ids_links(route_link)
        
        #add information for routes database
        #query = db.insert(self.routes_table)
        
        
        #self.connection.execute(query,[{'route_id': id_} for id_ in ids])
        
        #set_trace()
        for i in range(len(ids)):
            start = time.time()
            if ids[i] not in self.route_id_dict:
                time.sleep(self.urlopen_delay)
                self.scrape_route_data(ids[i],route_links[i])
                
                time.sleep(self.urlopen_delay)
                self.get_users_who_rated_route(route_links[i],ids[i])
                
            #periodically dump data
            if i % 50 == 0:
                #pickle dump
                pickle.dump(self.route_id_dict, open( "route_table.p", "wb" ) )
                pickle.dump(self.user_id_dict, open( "user_table.p", "wb" ) )
                #
                
                #update user on progress
                end = time.time()
                if self.verbatim:
                    print('route index ',i,' completed of ',len(ids),' in ',end-start, 'seconds')
                
        #end add information for routes database
        
        self.connection.close()
        self.engine.dispose()
        
        #pickle dump
        pickle.dump(self.route_id_dict, open( "route_table.p", "wb" ) )
        pickle.dump(self.user_id_dict, open( "user_table.p", "wb" ) )
        #
        
        #set_trace()
            
    #TODO
    def find_master_area(self, dirurl = 'https://www.mountainproject.com/route-guide'):
        
        content_route_dir, link_route_dir, text_route_dir = \
            self.get_route_level_data(BeautifulSoup(urlopen(dirurl),'html.parser'),'div','mb-half',stop_ind=50)           
    
    def get_all_route_ids_links(self,route_link):
        
        route_links = self.flatten(self.extract_routes(route_link))
        #set_trace()
        
        route_ids = []
        
        #clean out all Nones
        if isinstance(route_links,list):
            for i in range(len(route_links)):
                link = route_links[i]
                
                if link == None:
                    continue
                
                #for some reason, some non-route links make it through, delete these
                if 'route' not in link.split('/'):
                    route_links[i] = None
                else:
                    route_ids.append(int(self.get_id(link)))
                    
            route_links = [y for y in route_links if y != None]
        else:
            route_ids.append(int(self.get_id(route_links)))
            
        return route_ids,route_links
    
    #extract_routes and flatten get only the routes (lead nodes of the area-route tree)
    def extract_routes(self,nest):
        if isinstance(nest,list):
            if len(nest)>1:
                if not isinstance(nest[0],list) and isinstance(nest[1],list):
                    return [self.extract_routes(l) for l in nest[1]]
                else:
                    return [self.extract_routes(l) for l in nest]
            else:
                return nest
        else:
            if nest:
                return nest
            
    #TODO this did not work for all cases
#    def flatten(self,nested):
#        if all(type(x) == list for x in nested):
#            return sum(map(self.flatten, nested), [])
#        return nested
#    def flatten(self,nest):
#        set_trace()
#        if isinstance(nest[0],str):
#            return nest
#        
#        for i in nest:
#            if isinstance(i, list):
#                for j in self.flatten(i):
#                    return j
#            else:
#                return i
    
    def flatten(self,x):
        if isinstance(x, collections.Iterable) and not isinstance(x, str):
            return [a for i in x for a in self.flatten(i)]
        else:
            return [x]
    
    def scrape_route_data(self,id_,link):
        
        url = 'https://www.mountainproject.com/data/get-routes?routeIds='+str(id_)+'&key='+self.mp_api_key
        
        r = requests.get(url)
        json_data = r.json()
        json_data = json_data['routes'][0]
        
        route_name = json_data['name']
        route_rating = json_data['rating']
        route_type = json_data['type']
        route_avg_stars = json_data['stars']
        route_n_star_votes = json_data['starVotes']
        route_pitches = json_data['pitches']
        route_location = json_data['location']
        route_long = json_data['longitude']
        route_lat = json_data['latitude']
        
        #query = db.update(self.routes_table).values(route_name = route_name)
        #query = query.where(self.routes_table.columns.route_id == id_)
        #self.connection.execute(query)
        
        self.route_id_dict[id_] = {'route_name': route_name, 
                                   'route_rating': route_rating,
                                   'route_type': route_type,
                                   'route_avg_stars': route_avg_stars,
                                   'route_n_star_votes':route_n_star_votes,
                                   'route_pitches':route_pitches,
                                   'route_location':route_location,
                                   'route_long':route_long,
                                   'route_lat':route_lat,
                                   'url':link}
        
    #input link of route page, outputs all the users and their ratings for that particular route
    def get_users_who_rated_route(self,link,route_id):
        #stat page of route
        stats_link = link[:37]+'/stats'+link[37:]
        
        r = requests.get(stats_link)

        soup = BeautifulSoup(r.text,'html5lib')
                
        content = soup.find('table',\
                           class_='table table-striped')
        
        table_rows = content.find_all('tr')
        
        #go through the ratings and add them to list
        #user_link = []
        #nstars = []
        for i in range(len(table_rows)):
            table_data = table_rows[i].find_all('td')
            
            #all user links
            user_link = table_data[0].find('a')['href']
            user_id = self.get_id(user_link)
            
            #if somehow, we're unable to recover user_id just skip
            if user_id == None:
                set_trace()
                continue
            
            user_star_rating = len(table_data[1].find_all('img'))
            
            if user_id not in self.user_id_dict:
                self.user_id_dict[user_id] = {route_id:user_star_rating}
            else:
                self.user_id_dict[user_id][route_id] = user_star_rating
            
            #the corresponding user star rating of route
            #nstars.append(len(table_data[1].find_all('img')))
        
        
#    def scrape_MP(self):
#        
#        content_route_dir, link_route_dir, text_route_dir = \
#            self.get_route_level_data(self.root_soup,'div','mb-half',stop_ind=self.stop_ind_vect[0])
#            
#        for rdind in range(len(link_route_dir)):
#            if self.verbatim:
#                print(text_route_dir[rdind], link_route_dir[rdind])
#            
#            time.sleep(self.urlopen_delay)
#            state_soup = BeautifulSoup(urlopen(link_route_dir[rdind]),'html.parser')
#            
#            #get data for climbing regions within state
#            content_region, link_region, text_region = self.get_route_level_data(state_soup,'div','lef-nav-row',stop_ind=2)
#            
#            for regind in range(len(link_region)):
#                if self.varbatim:
#                    print('\t',text_region[regind],link_region[regind])
#                
#                time.sleep(self.urlopen_delay)
#                reg_soup = BeautifulSoup(urlopen(link_region[regind]),'html.parser')
#                
#                content_area, link_area, text_area = \
#                    self.get_route_level_data(reg_soup,'div','lef-nav-row')
#                
#                #if content area is empty, check for routes instead
#                if not content_area:
#                    #set_trace()
#                    content_route, link_route, text_route = \
#                        self.get_route_level_data(reg_soup,'table','width100',id_name='left-nav-route-table',is_route_level=True)
#                        
#                    #set_trace()
#                    for routeind in range(len(text_route)):
#                        if self.verbatim:
#                            print('\t\t\t',text_route[routeind],link_route[routeind])
#                else:
#                    for areaind in range(len(content_area)):
#                        if self.verbatim:
#                            print('\t\t',text_area[areaind],link_area[areaind])
#                        
#                        time.sleep(self.urlopen_delay)
#                        area_soup = BeautifulSoup(urlopen(link_area[areaind]),'html.parser')
#                        
#                        #set_trace()
#                        content_route, link_route, text_route = \
#                            self.get_route_level_data(area_soup,'table','width100',id_name='left-nav-route-table',is_route_level=True)
#                        
#                        for routeind in range(len(text_route)):
#                            print('\t\t\t',text_route[routeind],link_route[routeind])