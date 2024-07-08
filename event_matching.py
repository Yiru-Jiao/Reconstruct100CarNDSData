'''
This script matches the event target with one of the surrounding vehicles detected by the radar.
Note that this matching is very basic and may be incorrect due to such as
1) detection failure of the target vehicle
2) noise introduced in the process of trajectory reconstruction
'''

import pandas as pd

path_cleaned = './CleanedData/'
path_processed = './ProcessedData/'
path_matched = './MatchedEvents/'


# These target will not be counted in matching due to either
# 1) the target is not a vehicle
# or 2) the target is a vehicle but not interacting with the ego vehicle
# or 3) the target information is not available
uncounted_target = ['Single vehicle conflict', 'obstacle/object in roadway', 'parked vehicle', 'Other']

for crash_type in ['Crash', 'NearCrash']:
    print('Processing ', crash_type, ' data...')

    data_ego = pd.read_hdf(path_processed + 'HundredCar_'+crash_type+'_Ego.h5', key='data')
    data_sur = pd.read_hdf(path_processed + 'HundredCar_'+crash_type+'_Surrounding.h5', key='data')
    meta = pd.read_csv(path_cleaned + 'HundredCar_metadata_'+crash_type+'Event.csv').set_index('webfileid')
    meta = meta.loc[data_ego['trip_id'].unique()]
    meta = meta[~meta['target'].isin(uncounted_target)]

    print(f'There are {data_ego['trip_id'].nunique()} trips processed')

    events = []
    for trip_id in meta.index:

        df_ego = data_ego[data_ego['trip_id'] == trip_id]
        df_sur = data_sur[data_sur['trip_id'] == trip_id]
        if df_sur['target_id'].nunique()==0:
            print('Trip {} has no surrounding data available\n'.format(trip_id))
        else:
            print('Trip {} has {} surrounding vehicles\n'.format(trip_id, df_sur['target_id'].nunique()))
            merged = df_ego[df_ego['event'].astype(bool)].merge(df_sur, on='time', suffixes=('_ego', '_sur'))
            forward = merged[merged['forward'].astype(bool)].groupby('target_id')['range'].min().sort_values()
            rearward = merged[~merged['forward'].astype(bool)].groupby('target_id')['range'].min().sort_values()
            merged = merged.groupby('target_id')['range'].min().sort_values()

            if ('lead' in meta.loc[trip_id]['target']) and (len(forward)>0):
                target_id = forward.index[0]
            elif ('follow' in meta.loc[trip_id]['target']) and (len(rearward)>0):
                target_id = rearward.index[0]
            else:
                target_id = merged.index[0]

            veh_i = df_ego[['time','x_ekf','y_ekf','psi_ekf','v_ekf','trip_id','event']].copy()
            veh_i = veh_i.rename(columns={'x_ekf':'x','y_ekf':'y','psi_ekf':'psi','v_ekf':'speed'})
            veh_i[['width','length']] = meta.loc[trip_id][['ego_width','ego_length']].values.astype(float)

            veh_j = df_sur[df_sur['target_id']==target_id][['time','x_ekf','y_ekf','psi_ekf','v_ekf','target_id','range','forward']].copy()
            veh_j = veh_j.rename(columns={'x_ekf':'x','y_ekf':'y','psi_ekf':'psi','v_ekf':'speed'})
            veh_j[['width','length']] = meta.loc[trip_id][['target_width','target_length']].values.astype(float)

            df = veh_i.merge(veh_j, on='time', suffixes=('_i', '_j'), how='inner')
            if df[df['event'].astype(bool)]['range'].min()<4.5: # so that no other vehicles can be between the ego and the target during event
                events.append(df)

    events = pd.concat(events)
    events.to_hdf(path_matched + 'HundredCar_' + crash_type + 'es.h5', key='data')

    meta = meta.loc[events['trip_id'].unique()]
    meta.to_csv(path_matched + 'HundredCar_metadata_' + crash_type + 'es.csv')
    print(f'There are {len(meta)} {crash_type}es matched and saved.')

