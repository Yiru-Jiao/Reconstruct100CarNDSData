'''
This script preprocesses the 100-Car Naturalistic Driving Study data.
The raw data is publicly available at https://doi.org/10.15787/VTT1/CEU6RB
'''

import pandas as pd

path_raw = './RawData/'
path_cleaned = './CleanedData/'


# Meta data processing

## Ego vehicle information
ego_vehicle = pd.read_csv(path_raw + '100CarVehicleInformation.csv')
### Vehicle dimensions source: https://www.auto123.com
ego_vehicle.loc[(ego_vehicle['make']=='Ford')&(ego_vehicle['model']=='Taurus'), ['width','length']] = [1.854, 5.017]
ego_vehicle.loc[(ego_vehicle['make']=='Chevrolet')&(ego_vehicle['model']=='Malibu'), ['width','length']] = [1.763, 4.836]
ego_vehicle.loc[(ego_vehicle['make']=='Toyota')&(ego_vehicle['model']=='Camry'), ['width','length']] = [1.780, 4.785]
ego_vehicle.loc[(ego_vehicle['make']=='Toyota')&(ego_vehicle['model']=='Corolla'), ['width','length']] = [1.695, 4.420]
ego_vehicle.loc[(ego_vehicle['make']=='Chevrolet')&(ego_vehicle['model']=='Cavalier'), ['width','length']] = [1.744, 4.595]
ego_vehicle.loc[(ego_vehicle['make']=='Ford')&(ego_vehicle['model']=='Explorer'), ['width','length']] = [1.782, 4.579]
ego_vehicle.loc[ego_vehicle['width'].isna(), ['width','length']] = [1.8, 4.5]

## target vehicle information
data_event = pd.read_csv(path_raw + '100CarEventVideoReducedData.csv')
vehicle_dimension = {} 
### estimated by ChatGPT 4
vehicle_dimension['Automobile'] = {'width': 1.8, 'length': 4.5}
vehicle_dimension['Pickup truck'] = {'width': 1.9, 'length': 5.9}
vehicle_dimension['Tractor-trailer: Enclosed box'] = {'width': 2.6, 'length': 22.5}
vehicle_dimension['Sport Utility Vehicles'] = {'width': 2.0, 'length': 4.8}
vehicle_dimension['Van (minivan or standard van)'] = {'width': 2.1, 'length': 5.5}
vehicle_dimension['School bus'] = {'width': 2.4, 'length': 10.5}
vehicle_dimension['Single-unit straight truck: Box'] = {'width': 2.4, 'length': 7.3}
vehicle_dimension['Transit bus'] = {'width': 2.6, 'length': 11.5}
vehicle_dimension['Single-unit straight truck: Flatbed'] = {'width': 2.4, 'length': 7.3}
vehicle_dimension['Single-unit straight truck: Tow truck'] = {'width': 2.4, 'length': 8.9}
vehicle_dimension['Single-unit straight truck: Dump'] = {'width': 2.4, 'length': 7.3}
vehicle_dimension['Single-unit straight truck: Multistop/Step Van'] = {'width': 2.1, 'length': 6.4}
vehicle_dimension['Tractor-trailer: Tank'] = {'width': 2.6, 'length': 22.5}
vehicle_dimension['Other vehicle type'] = {'width': 1.8, 'length': 4.5}
vehicle_dimension['Unknown vehicle type'] = {'width': 1.8, 'length': 4.5}
vehicle_dimension = pd.DataFrame(vehicle_dimension).T
## ignore events with infrastructure, cyclist, pedestrian, motorcyclist, animal, and unknown target
data_event = data_event[data_event['target type'].isin(vehicle_dimension.index)].copy()
data_event['target_width'] = data_event['target type'].map(vehicle_dimension['width'])
data_event['target_length'] = data_event['target type'].map(vehicle_dimension['length'])
data_event[['ego_width','ego_length']] = ego_vehicle.set_index('vehicle webid').loc[data_event['vehicle webid']][['width','length']].values

## correct event start if it's 0
data_event.loc[data_event['event start']==0, 'event start'] = 1

## save meta data
crash_event = data_event[data_event['event severity']=='Crash']
nearcrash_event = data_event[data_event['event severity']=='Near-Crash']

crash_event.to_csv(path_cleaned + 'HundredCar_metadata_CrashEvent.csv', index=False)
nearcrash_event.to_csv(path_cleaned + 'HundredCar_metadata_NearCrashEvent.csv', index=False)


# Time-series data processing

for crash_type in ['Crash','NearCrash']:
    data_raw = pd.read_csv(path_raw + 'HundredCar_'+crash_type+'_Public_Compiled.txt', 
                           sep=',',
                           converters={77: lambda x: x.strip().replace('"', '').replace('.', 'NA'),
                                       8: lambda x: 'NA' if x=='.' else x,
                                       9: lambda x: 'NA' if x=='.' else x})
    data_raw.to_csv(path_cleaned + 'HundredCar_'+crash_type+'_Public_Cleaned.csv', index=False)
