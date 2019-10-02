#debug MPR recommender

from MPR import MP_Recommender

with open('MP_api_key.ini','r') as content_file:
    api_key = content_file.read()

mpr = MP_Recommender('user_table.p',
                     'route_table.p',
                     'df_routes.p',
                     'df20.p',
                     api_key)

user_id = 200441537 #holly's account, does not work, TODO: debug


mpr.load_prev_content_results('similarity_results.p')
recs,top_n_rated = mpr.get_user_recs(user_id)

for r in recs:
    #print(mpr.route_id_dict[r]['route_name'])
    print(mpr.route_id_dict[r]['url'])