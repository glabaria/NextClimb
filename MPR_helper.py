from MPR import MP_Recommender

with open('MP_api_key.ini','r') as content_file:
    api_key = content_file.read()

mpr = MP_Recommender('user_table.p',
                     'route_table.p',
                     'df_routes.p',
                     'df20.p',
                     api_key)

#user_id = 200128311 #mine, trad, alpine, intermediate
#user_id = 110596403 #boulder-er
#user_id = 200272475 #boulder-er, advanced
#200128311 boulder-er
#user_id = 200077815 #michaels, trad, alpine, intermediate
#user_id = 106540415 #mixed climber, alpine climber, advanced
user_id = 200441537

#mpr.load_prev_colab_results(user_id)
#mpr.print_recs(user_id)

mpr.load_prev_content_results('similarity_results.p')
recs,top_n_rated = mpr.get_user_recs(user_id)