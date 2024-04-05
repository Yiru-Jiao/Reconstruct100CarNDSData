'''
This script processes the cleaned data of 100-Car Naturalistic Driving Study.
'''
from tqdm import tqdm
import pandas as pd
import numpy as np
from utils_data import *

path_cleaned = './CleanedData/'
path_processed = './ProcessedData/'


for crash_type in ['Crash','NearCrash']:
    invalid_trips = []
    print('Processing', crash_type, 'data...')

    # data loading
    data = pd.read_csv(path_cleaned + 'HundredCar_'+crash_type+'_Public_Cleaned.csv')
    data = data.set_index('trip_id')
    meta = pd.read_csv(path_cleaned + 'HundredCar_metadata_'+crash_type+'Event.csv')
    meta = meta.set_index('webfileid')

    # data processing
    data_ego = []
    data_sur = []
    trip_list = meta.index.values
    target_id = 0 # Initialize target_id for surrounding vehicles detected by radar
    for trip in tqdm(trip_list):
        sample = data.loc[trip].reset_index().values
        ## create dataframe
        df_ego, df_forward, df_rearward = create_dataframe(sample, target_id)

        ## reconstruct ego trajectory and make comparison plots
        fig_path = path_processed + 'plots_ekf/' + crash_type + '/'
        df_ego, valid = process_ego(df_ego, trip, fig_path)
        if not valid:
            invalid_trips.append(trip)
            continue
        ## reconstruct surrounding vehicle trajectory
        ego_length = meta.loc[trip]['ego_length']
        if len(df_forward)>0:
            df_forward = df_forward[(df_forward['range']>=0)]
            if len(df_forward)>0:
                df_forward = process_surrounding(df_ego, df_forward, ego_length, forward=True)
                df_forward['forward'] = 1
        if len(df_rearward)>0:
            df_rearward = df_rearward[(df_rearward['range']>=0)]
            if len(df_rearward)>0:
                df_rearward = process_surrounding(df_ego, df_rearward, ego_length, forward=False)
                df_rearward['forward'] = 0
        if len(df_forward)>0 or len(df_rearward)>0:
            df_sur = pd.concat([df_forward, df_rearward])
        
        ## select segments covering the event
        time_start = df_ego[df_ego['sync']==meta.loc[trip]['event start']]['time'].values[0]
        time_end = df_ego[df_ego['sync']==meta.loc[trip]['event end']]['time'].values[0]
        df_ego.loc[(df_ego['time']>=time_start)&(df_ego['time']<=time_end), 'event'] = 1
        df_ego.loc[df_ego['event'].isna(), 'event'] = 0
        df_sur = df_sur[(df_sur.groupby('target_id')['time'].transform('min')<=time_start)&
                        (df_sur.groupby('target_id')['time'].transform('max')>time_start)]

        ## append dataframes
        data_ego.append(df_ego)
        data_sur.append(df_sur)
        target_id += 1

    # save dataframes
    data_ego = pd.concat(data_ego)
    data_sur = pd.concat(data_sur)
    data_ego[['trip_id','sync','event']] = data_ego[['trip_id','sync','event']].astype(int)
    data_sur[['trip_id','target_id','forward']] = data_sur[['trip_id','target_id','forward']].astype(int)

    data_ego.to_hdf(path_processed + 'HundredCar_'+crash_type+'_Ego.h5', key='data')
    data_sur.to_hdf(path_processed + 'HundredCar_'+crash_type+'_Surrounding.h5', key='data')
    
    # save invalid trips
    invalid_trips = np.array(invalid_trips)
    np.savetxt(path_processed + 'HundredCar_'+crash_type+'_DataLacked.txt', invalid_trips, fmt='%d', delimiter=',')