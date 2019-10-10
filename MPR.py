import pickle
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
from surprise import Dataset
from surprise import Reader
from surprise import accuracy
from surprise import SVD
from surprise import SVDpp
from surprise.model_selection import train_test_split
from surprise import dump
import string
#import nltk
#import sklearn
#from sklearn.metrics.pairwise import linear_kernel
import requests
import random
from IPython.core.debugger import set_trace

class MP_Recommender(object):
    def __init__(self,
                 user_table_filename,
                 route_table_filename,
                 df_routes_filename,
                 df_routes_at_least20_filename,
                 mp_api_key,
                 verbatim=False):
        
        self.verbatim = verbatim
        self.route_id_dict = pickle.load( open( route_table_filename, "rb" ) )
        self.user_id_dict = pickle.load( open( user_table_filename, "rb" ) )
        self.df_routes = pickle.load( open( df_routes_filename, "rb" ) )
        self.df20 = pickle.load( open (df_routes_at_least20_filename, "rb"))
        
        self.mp_api_key = mp_api_key
        
        user_ids = []
        frames = []
        
        for user_id, d in self.user_id_dict.items():
            user_ids.append(user_id)
            frames.append(pd.DataFrame.from_dict(d, orient='index'))

        df = pd.concat(frames, keys=user_ids)
        
        df2 = df.unstack(level=-1)
        df3 = df2[0]
        
        #pd DF of the users (user id as index) with their associated ratings by route_id
        df3.index.name = 'user_id'
        self.df_users = df3
        
        #self.build_user_rating_df()
                      
    #this function helps set up all the data structures necessary for the user-rating matrix
    def build_user_rating_df(self):
        user_ids = []
        frames = []
        
        for user_id, d in self.user_id_dict.items():
            user_ids.append(user_id)
            frames.append(pd.DataFrame.from_dict(d, orient='index'))

        df = pd.concat(frames, keys=user_ids)
        
        df2 = df.unstack(level=-1)
        df3 = df2[0]
        
        #pd DF of the users (user id as index) with their associated ratings by route_id
        df3.index.name = 'user_id'
        self.df_users = df3
        
        #convert to numpy array for possible visualization
        user_rating_mat = self.df_users.to_numpy().copy()
        user_rating_mat[np.isnan(user_rating_mat)] = 0.0
        
#        if self.verbatim:
#            fig = plt.figure(figsize=(22,22))
#            plt.spy(user_rating_mat,markersize=0.5)
#            plt.xlabel('Route ID',fontsize=24)
#            plt.ylabel('User ID',fontsize=24)
#            plt.title('User-Rating Matrix',fontsize=24)
#            plt.rcParams['xtick.labelsize']=20
#            plt.rcParams['ytick.labelsize']=20
#            fig.savefig('sparsity.png') # Use fig. here
#            plt.show()
            
        #get users who have rated at least n=15 routes
        ind_users_at_least20 = []

        dim = user_rating_mat.shape
        for u in range(dim[0]):
            n = len(user_rating_mat[u,:].nonzero()[0])
            if n >= 15:
                ind_users_at_least20.append(u)
                
        #print(df_users.index[ind_users_at_least20])
        
        df_users_at_least20 = self.df_users.loc[self.df_users.index[ind_users_at_least20]]
        
        df20=df_users_at_least20.stack()
        df20 = df20.reset_index()
        df20.columns = ['user_id','route_id','rating']
        #Pandas DF that has user_id, route_id, and rating; i.e., all the users and their ratings
        self.df20 = df20
        
    def run_colab_filter(user_id,self):
        # A reader is still needed but only the rating_scale param is requiered.
        reader = Reader(rating_scale=(1, 4))
        
        # The columns must correspond to user id, item id and ratings (in that order).
        data = Dataset.load_from_df(self.df20[['user_id', 'route_id', 'rating']], reader)

        # Retrieve the trainset.
        trainset = data.build_full_trainset()
        
        # Than predict ratings for all pairs (u, i) that are NOT in the training set.
        testset = trainset.build_anti_testset()

        algo_tuned = SVDpp(n_factors=20)
        algo_tuned.fit(trainset)
        
        iid = self.df20['route_id'].unique()
        #user_id = 200128311 #mine, trad, alpine, intermediate
        #user_id = 110596403 #boulder-er
        #user_id = 200272475 #boulder-er, advanced
        #user_id = 111344588 #boulder-er
        #user_id = 200077815 #michaels, trad, alpine, intermediate
        #user_id = 106540415 #mixed climber, alpine climber, advanced
        iid_me = self.df20.loc[self.df20['user_id']==user_id,'route_id'].values #all the route ids that user climbed
        iids_to_pred = np.setdiff1d(iid,iid_me) #all the route ids to predict
        
        testset = [[user_id,iid,2] for iid in iids_to_pred]
        predictions_tuned = algo_tuned.test(testset)
        
        dump.dump(file_name='SVD_tuned.p',predictions=predictions_tuned,algo=algo_tuned)
        
        pred_ratings_tuned = np.array([pred.est for pred in predictions_tuned])

        i_max = np.argpartition(pred_ratings_tuned,-20)[-20:]
        i_max = i_max[np.argsort(-pred_ratings_tuned[i_max])]
        
        iid = iids_to_pred[i_max]
                   
        #top 20 recommended climbs
        self.df_top_climbs_mf=pd.DataFrame(iid,pred_ratings_tuned[i_max])
        self.df_top_climbs_mf = self.df_top_climbs.reset_index()
        
        self.df_top_climbs_mf.columns=['predicted rating','route id']
        
    def load_prev_colab_results(self,user_id,colab_model_filename='NMF_tuned.p'):
        (_,algo_tuned) = dump.load(colab_model_filename)
        
        iid = self.df20['route_id'].unique()
        #user_id = 200128311 #mine, trad, alpine, intermediate
        #user_id = 110596403 #boulder-er
        #user_id = 200272475 #boulder-er, advanced
        #user_id = 111344588 #boulder-er
        #user_id = 200077815 #michaels, trad, alpine, intermediate
        #user_id = 106540415 #mixed climber, alpine climber, advanced
        iid_me = self.df20.loc[self.df20['user_id']==user_id,'route_id'].values #all the route ids that user climbed
        iids_to_pred = np.setdiff1d(iid,iid_me) #all the route ids to predict
        testset = [[user_id,iid,2] for iid in iids_to_pred]
        predictions_tuned = algo_tuned.test(testset)
        
        pred_ratings_tuned = np.array([pred.est for pred in predictions_tuned])

        i_max = np.argpartition(pred_ratings_tuned,-20)[-20:]
        i_max = i_max[np.argsort(-pred_ratings_tuned[i_max])]
        iid = iids_to_pred[i_max]
                   
        #top 20 recommended climbs
        self.df_top_climbs_mf = pd.DataFrame(iid,pred_ratings_tuned[i_max])
        self.df_top_climbs_mf = self.df_top_climbs_mf.reset_index()
        
        self.df_top_climbs_mf.columns=['predicted rating','route id']
        
    def build_routes_df(self):
        route_ids = []
        frames = []
        
        for route_id, d in self.route_id_dict.items():
            route_ids.append(route_id)
            frames.append(pd.DataFrame.from_dict(d, orient='index'))
        
        df = pd.concat(frames, keys=route_ids)    
        df2 = df.unstack(level=-1)      
        df3 = df2[0]
        df3.index.name = 'route_id'
        self.df_routes = df3
    
    #makes document containing text descripting route for each route
    def make_route_document(self):
        nltk.download('stopwords')

        stopwords = set(nltk.corpus.stopwords.words('english') + ['california','climb','rock'])
        stemmer = nltk.stem.PorterStemmer()
        
        route_text = {}
        for route_id, route_details in self.df_routes.iterrows():
            #join the relevent features of the climbing route to create a document
            if route_details['grade'] == None:
                grade = ''
            else:
                grade = 'grade'+str(route_details['grade'])
                
            if pd.isnull(route_details['desc']):
                route_details['desc'] = ''
            
            content = route_details['desc'] + ' ' + route_details['route_rating'] + ' ' + \
                        route_details['route_type'] + ' ' + ' '.join(route_details['route_location']) + ' ' +\
                        grade
            
            #pre-processing, make all words lowercase and remove punctuation
            content = content.lower()
            table = str.maketrans('', '', string.punctuation)
            content = content.translate(table)
            
            # Create stopwords list, convert to a set for speed
            content = [word for word in content.split() if word not in stopwords]
            
            content = " ".join([stemmer.stem(word) for word in content])
        
            route_text[route_id] = content
            
        self.route_text_df = pd.DataFrame.from_dict(route_text,orient='index',columns=['route_text'])
        self.route_text_df.index.name = 'route_id'
        
        return route_text
        
    def build_tfidf_matrix(self, route_text):
        route_text_list = []
        for key in self.route_text:
            route_text_list.append(self.route_text[key])
            
        # Generate tf-idf object with maximum vocab size of 1000
        tf_counter = sklearn.feature_extraction.text.TfidfVectorizer(max_features = 1000)
        # Get tf-idf matrix as sparse matrix
        tfidf = tf_counter.fit_transform(route_text_list)
        
        return tfidf
    
    #builds cosine similarity matrix, creates global variable similarity_dict that
    #gives the 30 most similar climbs with key being the MP route id
    def build_cosine_similarity(self, tfidf):
        cosine_similarities = linear_kernel(tfidf, tfidf)

        results = {} # dictionary created to store the result in a dictionary format (ID : (Score,item_id))#
        for idx, row in self.route_text_df.iterrows(): #iterates through all the rows
        
            # the below code 'similar_indice' stores similar ids based on cosine similarity. sorts them in ascending order. [:-5:-1] is then used so that the indices with most similarity are got. 0 means no similarity and 1 means perfect similarity#
            similar_indices = cosine_similarities[self.route_text_df.index.get_loc(idx)].argsort()[:-31:-1]
        
            #stores 30 most similar routes, you can change it as per your needs
            similar_items = [(cosine_similarities[self.route_text_df.index.get_loc(idx)][i], self.route_text_df.index[i]) for i in similar_indices]
            results[idx] = similar_items[1:]
            
        self.similarity_dict = results
        
    def load_prev_content_results(self, similarity_filename, mostpopular_filename='recs_list_popular.p'):
        self.similarity_dict = pickle.load( open( similarity_filename, "rb" ) )
        
        self.similarity_df = pd.DataFrame.from_dict(self.similarity_dict)
        
        self.most_popular = pickle.load(open(mostpopular_filename,"rb"))
        
    def get_content_recs(self, route_id):
        return self.similarity_df[[route_id]]
    
    def get_user_info_from_MP(self,user_id):
        url = 'https://www.mountainproject.com/data/get-user?userId='+str(user_id)+'&key='+self.mp_api_key

        r = requests.get(url)
        
        #if goes here, the user is not valid
        if not r.text:
            return False
        
        json_data = r.json()
    
        user_name = json_data['name']
        user_avatar_url = json_data['avatar']
    
        self.user_info = {'user_name':user_name, 'user_avatar_url':user_avatar_url}
        
        return True
        
    #gets recommendations on climb based on collaborative and content-based filtering
    #start_top_n_index: this starts the top n rated climbs index.
    #for example, start_top_n_index = 3 bases the content recommender on the top
    #3,4,5,6,7 user rated climbs
    def get_user_recs(self,user_id,make_requests=True,colab_model_filename='NMF_tuned.p',
                      content_recs_only=False, start_top_n_index=0, start_modcounter_index=0,
                      is_first_run=True):
        
        #flag for if the user has cycled through all the recommendations
        self.is_last_nextrec = False
        
        #deal with users not in dataset (cold-start)
        if user_id not in self.df_users.index:
            self.is_last_nextrec = True
            
            if make_requests:
                #check to make sure user is actually registered on MP
                is_user_exist = self.get_user_info_from_MP(user_id)
                
            #handle not registered users
            if not is_user_exist:
                return None, 0
            
            #if code is here, the user exists on MP, but has not rated any
            #indexed routes by our system; in this case, just recommend some
            #of the more popular routes
            recs = random.sample(list(self.most_popular.values), 20)
            
            recs_img_url = {}
            for rr in recs:
                url = 'https://www.mountainproject.com/data/get-routes?routeIds='+str(rr)+'&key='+self.mp_api_key
            
                r = requests.get(url)
                json_data = r.json()
                recs_img_url[rr] = json_data['routes'][0]['imgSmall']
            self.recs_img_url = recs_img_url
            
            return recs, 0
        
        else:
            if make_requests and is_first_run:
                url = 'https://www.mountainproject.com/data/get-user?userId='+str(user_id)+'&key='+self.mp_api_key
    
                r = requests.get(url)
                json_data = r.json()
            
                user_name = json_data['name']
                user_avatar_url = json_data['avatar']
            
                self.user_info = {'user_name':user_name, 'user_avatar_url':user_avatar_url}
            
            if is_first_run:
                user_routes_rated = self.df_users.iloc[self.df_users.index.get_loc(user_id),:]
            
                user_routes_rated = user_routes_rated[user_routes_rated.notnull()]
                n_rated = len(user_routes_rated)
            
            user_routes_rated.sort_values(axis=0,ascending=False,inplace=True)
            if n_rated >=5:
                if n_rated >= start_top_n_index+5:
                    top_rated = user_routes_rated[start_top_n_index:start_top_n_index+5]
                else:
                    while start_top_n_index+5 > n_rated:
                        start_top_n_index -= 1
                        
                    top_rated = user_routes_rated[start_top_n_index:start_top_n_index+5]
            else:
                top_rated = user_routes_rated
                
            recs = []
            
            n_top_rated = len(top_rated)
            max_sim = len(self.similarity_df)
            
            #if number of climbs user rated is >=20, this user was included in the matrix-factorization
            #all other users treated in the cold-start problem (only based on content-based filtering)
            if n_rated >= 20 and not content_recs_only:
                if is_first_run:
                    self.load_prev_colab_results(user_id,colab_model_filename=colab_model_filename)
                    #top climbs from matrix factorization (colab based)
                    top_mf = self.df_top_climbs_mf[['route id']].to_numpy()
                
                #set_trace()
                modcount = 3*start_modcounter_index
                for i in range(n_top_rated*3):
                    #set_trace()
                    if modcount >= max_sim:
                        self.is_last_nextrec = True
                        break
                    
                    curr_rec = self.get_content_recs(top_rated.index[i%n_top_rated]).iloc[modcount].to_numpy()[0][1]
                    
                    #if current recommendation was already recommended recommend a different item
                    counter = 1
                    while curr_rec in recs or curr_rec in top_rated.index:
                        if modcount+counter >= max_sim:
                            self.is_last_nextrec = True
                            break
                        
                        curr_rec = self.get_content_recs(top_rated.index[i%n_top_rated]).iloc[modcount+counter].to_numpy()[0][1]
                        counter += 1
                    #
                        
                    recs.append(curr_rec)
                    if i%n_top_rated == 0 and i > 0:
                        modcount += 1
                
                #last 5 recommendations are provided from MFs
                if start_modcounter_index*5+5 > 20:
                    for i in range(start_modcounter_index*5,20):
                        recs.append(top_mf[i][0])
                else:        
                    for i in range(start_modcounter_index*5,start_modcounter_index*5+5):
                        recs.append(top_mf[i][0])
                    
            elif n_rated < 20 or content_recs_only:
                modcount = 3*start_modcounter_index
                for i in range(20):
                    if modcount >= max_sim:
                        self.is_last_nextrec = True
                        break
                    
                    curr_rec = self.get_content_recs(top_rated.index[i%n_top_rated]).iloc[modcount].to_numpy()[0][1]
                    
                    counter = 1
                    while curr_rec in recs or curr_rec in top_rated.index:
                        if modcount+counter >= max_sim:
                            self.is_last_nextrec = True
                            break
                        curr_rec = self.get_content_recs(top_rated.index[i%n_top_rated]).iloc[modcount+counter].to_numpy()[0][1]
                        counter += 1
                    
                    recs.append(curr_rec)
            
                    if i%n_top_rated ==0 and i>0:
                        modcount += 1
                        
                    if modcount >= max_sim:
                        break
            
            if self.verbatim:
                print('recommendations for ',user_name, '(',str(user_id),'):')
                #print(*recs,sep='\n')
                for i in range(len(recs)):
                    print(i+1, ') ', recs[i], 
                         self.route_id_dict[recs[i]]['route_name'], ', ', 
                         self.route_id_dict[recs[i]]['route_rating'], ', ', 
                         '(',self.route_id_dict[recs[i]]['route_type'],'), ',
                         self.route_id_dict[recs[i]]['route_pitches'],' pitches, ',
                         'location: ', self.route_id_dict[recs[i]]['route_location'], ', ', 
                         'url: ', self.route_id_dict[recs[i]]['url'])
        
            if make_requests:
                #grab pictures for the routes from MP
                recs_img_url = {}
                for rr in recs:
                    url = 'https://www.mountainproject.com/data/get-routes?routeIds='+str(rr)+'&key='+self.mp_api_key
                
                    r = requests.get(url)
                    json_data = r.json()
                    recs_img_url[rr] = json_data['routes'][0]['imgSmall']
                self.recs_img_url = recs_img_url
                
                top_rated_img_url = []
                for i in range(n_top_rated):
                    url = 'https://www.mountainproject.com/data/get-routes?routeIds='+str(top_rated.index[i])+'&key='+self.mp_api_key
                
                    r = requests.get(url)
                    json_data = r.json()
                    
                    top_rated_img_url.append(json_data['routes'][0]['imgSmall'])
                self.top_rated = top_rated #top recommended climbs from MF
                self.top_rated_img_url = top_rated_img_url
            
        return recs,n_top_rated