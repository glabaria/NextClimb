from bs4 import BeautifulSoup
from urllib.request import urlopen
from configparser import ConfigParser
import time
import psycopg2

class MP_Scraper(object):
    def __init__(self,
                 route_page,
                 start_ind_vect=0,
                 stop_ind_vect=-1,
                 urlopen_delay=0.001,
                 verbatim=False,
                 initialize_db=False):
        
        page = urlopen(route_page)
        self.root_soup = BeautifulSoup(page,'html.parser')
        self.stop_ind_vect = stop_ind_vect
        self.urlopen_delay = urlopen_delay
        self.verbatim = verbatim
        self.is_area_complete_dict = {}
        
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
        if not id_name:
            content = soup.find_all(tag,class_=class_name)
        else:
            content = soup.find_all(tag,class_=class_name,id=id_name)
        
        counter = 0
        
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
        
    def scrape_MP(self):
        
        content_route_dir, link_route_dir, text_route_dir = \
            self.get_route_level_data(self.root_soup,'div','mb-half',stop_ind=self.stop_ind_vect[0])
            
        for rdind in range(len(link_route_dir)):
            if self.verbatim:
                print(text_route_dir[rdind], link_route_dir[rdind])
            
            time.sleep(self.urlopen_delay)
            state_soup = BeautifulSoup(urlopen(link_route_dir[rdind]),'html.parser')
            
            #get data for climbing regions within state
            content_region, link_region, text_region = self.get_route_level_data(state_soup,'div','lef-nav-row',stop_ind=2)
            
            for regind in range(len(link_region)):
                if self.varbatim:
                    print('\t',text_region[regind],link_region[regind])
                
                time.sleep(self.urlopen_delay)
                reg_soup = BeautifulSoup(urlopen(link_region[regind]),'html.parser')
                
                content_area, link_area, text_area = \
                    self.get_route_level_data(reg_soup,'div','lef-nav-row')
                
                #if content area is empty, check for routes instead
                if not content_area:
                    #set_trace()
                    content_route, link_route, text_route = \
                        self.get_route_level_data(reg_soup,'table','width100',id_name='left-nav-route-table',is_route_level=True)
                        
                    #set_trace()
                    for routeind in range(len(text_route)):
                        if self.verbatim:
                            print('\t\t\t',text_route[routeind],link_route[routeind])
                else:
                    for areaind in range(len(content_area)):
                        if self.verbatim:
                            print('\t\t',text_area[areaind],link_area[areaind])
                        
                        time.sleep(self.urlopen_delay)
                        area_soup = BeautifulSoup(urlopen(link_area[areaind]),'html.parser')
                        
                        #set_trace()
                        content_route, link_route, text_route = \
                            self.get_route_level_data(area_soup,'table','width100',id_name='left-nav-route-table',is_route_level=True)
                        
                        for routeind in range(len(text_route)):
                            print('\t\t\t',text_route[routeind],link_route[routeind])