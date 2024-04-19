'''
This script contains functions for data processing.
'''
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from utils_ekf import reconstruct_ego, reconstruct_surrounding


# Create dataframes for ego vehicle and surrounding vehicles
def create_dataframe(sample, target_id=0):
    df_ego = pd.DataFrame({'trip_id':sample[:,0],
                           'sync':sample[:,1], # frame sync for alignment
                           'time':sample[:,2], # unit: s
                           'speed_comp':sample[:,4], # unit: mph, -1 if not available
                           'speed_gps':sample[:,5], # unit: mph, -1 if not available
                           'yaw_rate':sample[:,6], # unit: deg/s, positive for left turn
                           'heading':sample[:,7], # unit: deg, 0=North, 90=East, 180=South, 270=West
                           'acc_lat':sample[:,8], # unit: g, positive for left turn
                           'acc_lon':sample[:,9], # unit: g
                           'brake':sample[:,77], # 0=off, 1=on
                           'signal':sample[:,78], # 0=off, 1=left, 2=right, 3=both
                           })

    df_forward = [pd.DataFrame()]
    targets = np.unique(sample[:,20:27])
    for target in targets[targets>0]:
        time = sample[:,2][np.where(sample[:,20:27]==target)[0]] # unit: s
        range = sample[:,34:41][np.where(sample[:,20:27]==target)] # unit: ft
        range_rate = sample[:,48:55][np.where(sample[:,20:27]==target)] # unit: ft/s, positive for increasing range
        azimuth = sample[:,62:69][np.where(sample[:,20:27]==target)] # unit: rad
        df_forward.append(pd.DataFrame({'time':time,'range':range,'range_rate':range_rate,'azimuth':azimuth,'target_id':target_id}))
        target_id += 1
    df_forward = pd.concat(df_forward)
    df_forward['trip_id'] = sample[0,0]

    df_rearward = [pd.DataFrame()]
    targets = np.unique(sample[:,27:34])
    for target in targets[targets>0]:
        time = sample[:,2][np.where(sample[:,27:34]==target)[0]]
        range = sample[:,41:48][np.where(sample[:,27:34]==target)]
        range_rate = sample[:,55:62][np.where(sample[:,27:34]==target)]
        azimuth = sample[:,69:76][np.where(sample[:,27:34]==target)]
        df_rearward.append(pd.DataFrame({'time':time,'range':range,'range_rate':range_rate,'azimuth':azimuth,'target_id':target_id}))
        target_id += 1
    df_rearward = pd.concat(df_rearward)
    df_rearward['trip_id'] = sample[0,0]

    return df_ego, df_forward, df_rearward



# reconstruct trajectory of the ego vehicle
def process_ego(df_ego, trip, fig_path):
    ego_params = {'uncertainty_init':100.,
                  'uncertainty_speed':10.,
                  'uncertainty_omega':5.,
                  'uncertainty_acc':5.,
                  'max_jerk':15.,
                  'max_yaw_rate':np.pi/2,
                  'max_acc':9.8,
                  'max_yaw_acc':np.pi*2}
    
    for acc in ['acc_lat','acc_lon']:
        if np.any(df_ego[acc].isna()):
            valid = np.logical_not(df_ego[acc].isna())
            interpolated = np.interp(df_ego['time'], df_ego['time'][valid], df_ego[acc][valid])
            df_ego[acc] = interpolated
    valid_start = np.all(df_ego['speed_comp'].iloc[:5]>=0)
    valid_end = np.all(df_ego['speed_comp'].iloc[-5:]>=0)
    if valid_start and not valid_end:
        reverse = False
        df_ego = reconstruct_ego(df_ego, ego_params.values(), reverse=False)
    elif valid_end and not valid_start:
        reverse = True
        df_ego = reconstruct_ego(df_ego, ego_params.values(), reverse=True)
    elif not valid_start and not valid_end:
        reverse = False
        print('\n Trip ', trip, ' lacks initial speed')
    elif valid_start and valid_end:
        df_order = reconstruct_ego(df_ego, ego_params.values(), reverse=False)
        df_reverse = reconstruct_ego(df_ego, ego_params.values(), reverse=True)
        to_count = (df_ego['speed_comp']>=0).values
        error_order = np.sum(np.abs(df_order['v_ekf'] - df_order['speed_comp']).values[to_count])
        error_reverse = np.sum(np.abs(df_reverse['v_ekf'] - df_reverse['speed_comp']).values[to_count])
        if error_order < error_reverse + to_count.sum()*0.02:
            reverse = False
            df_ego = df_order.copy()
            df_order = None
        else:
            reverse = True
            df_ego = df_reverse.copy()
            df_reverse = None
    
    ## plot and save reconstructed trajectory
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.5))
    if valid_start or valid_end:
        axes[0].plot(df_ego['time'], df_ego['v_ekf'], marker='o', color='tab:blue')
        axes[1].plot(df_ego['time'], df_ego['psi_ekf'], marker='o', color='tab:blue')
        axes[2].plot(df_ego['time'], df_ego['acc_ekf'], marker='o', label='ekf', color='tab:blue')
    axes[0].plot(df_ego['time'], df_ego['speed_comp'], alpha=0.5, marker='o', markersize=3, color='tab:orange')
    axes[0].set_xlabel('Time (s)')
    axes[0].set_title('Speed (m/s)')
    yaw = (np.cumsum(df_ego['yaw_rate']*np.gradient(df_ego['time']))).values
    yaw = (yaw + np.pi) % (2.0 * np.pi) - np.pi
    if reverse:
        yaw = yaw-yaw[-1]
    axes[1].plot(df_ego['time'], yaw, alpha=0.5, marker='o', markersize=3, color='tab:orange')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_title('Yaw (rad)')
    axes[2].plot(df_ego['time'], df_ego['acc_lon'], alpha=0.5, marker='o', markersize=3, label='raw', color='tab:orange')
    axes[2].set_xlabel('Time (s)')
    axes[2].set_title('Acceleration (m/s^2)')
    axes[2].legend(loc='lower left')

    if valid_start and valid_end:
        fig.suptitle('Trip id: '+str(trip)+', Reverse: '+str(reverse)+', Error in order: '+str(round(error_order,2))+', Error in reverse: '+str(round(error_reverse,2)),
                     y=1.05)
    else:
        fig.suptitle('Trip id: '+str(trip)+', Reverse: '+str(reverse), y=1.05)

    fig.savefig(fig_path + str(trip) + '.png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    
    return df_ego, valid_start|valid_end



# Rotate (x2t, y2t) to the coordinate system with the y-axis along (xyaxis, yyaxis)
def rotate_coor(xyaxis, yyaxis, x2t, y2t):
    x = yyaxis/np.sqrt(xyaxis**2+yyaxis**2)*x2t-xyaxis/np.sqrt(xyaxis**2+yyaxis**2)*y2t
    y = xyaxis/np.sqrt(xyaxis**2+yyaxis**2)*x2t+yyaxis/np.sqrt(xyaxis**2+yyaxis**2)*y2t
    return x, y



# Calculate the angle between the line of two vectors
def angle_degree(vec1x, vec1y, vec2x, vec2y):
    dot = vec1x*vec2x + vec1y*vec2y
    det = vec1x*vec2y - vec1y*vec2x
    angle = np.arctan2(det, dot)
    angle[angle<0] += np.pi
    angle[angle>np.pi/2] = np.pi - angle[angle>np.pi/2]    
    return angle*180/np.pi



# Process surrounding vehicles
def process_surrounding(df_ego, df_sur, ego_length, forward=True):
    df_sur[['range','range_rate']] = df_sur[['range','range_rate']]*0.3048
    df_ego_sur = df_ego.set_index('time').loc[df_sur['time'].values].reset_index()
    heading_ego = np.array([np.cos(df_ego_sur['psi_ekf'].values), np.sin(df_ego_sur['psi_ekf'].values)]).T
    heading_scale_ego = np.tile(np.sqrt(heading_ego[:,0]**2+heading_ego[:,1]**2), (2,1)).T
    point_head = df_ego_sur[['x_ekf','y_ekf']].values + heading_ego/heading_scale_ego*ego_length/2
    point_tail = df_ego_sur[['x_ekf','y_ekf']].values - heading_ego/heading_scale_ego*ego_length/2

    if forward:
        df_sur['azimuth'] = np.pi/2 - df_sur['azimuth']
        ego_reference_x = point_head[:,0]
        ego_reference_y = point_head[:,1] 
    else:
        df_sur['azimuth'] = np.pi*3/2 - df_sur['azimuth']
        ego_reference_x = point_tail[:,0]
        ego_reference_y = point_tail[:,1]

    local_dx = df_sur['range']*np.cos(df_sur['azimuth'])
    local_dy = df_sur['range']*np.sin(df_sur['azimuth'])
    global_dx, global_dy = rotate_coor(-np.cos(df_ego_sur['psi_ekf'].values),
                                    np.sin(df_ego_sur['psi_ekf'].values),
                                    local_dx.values, local_dy.values)
    df_sur['x'] = global_dx + ego_reference_x
    df_sur['y'] = global_dy + ego_reference_y
    delta_vx = df_sur['range_rate']*np.cos(df_sur['azimuth'])
    delta_vy = df_sur['range_rate']*np.sin(df_sur['azimuth'])
    delta_vx, delta_vy = rotate_coor(-np.cos(df_ego_sur['psi_ekf'].values),
                                    np.sin(df_ego_sur['psi_ekf'].values),
                                    delta_vx, delta_vy)
    df_sur['speed_comp'] = np.sqrt(((df_ego_sur['v_ekf']*np.cos(df_ego_sur['psi_ekf'])).values + delta_vx)**2 + 
                                   ((df_ego_sur['v_ekf']*np.sin(df_ego_sur['psi_ekf'])).values + delta_vy)**2)
    
    sur_params = {'uncertainty_init':1000.,
                  'uncertainty_pos':500.,
                  'uncertainty_speed':10.,
                  'max_acc':9.8,
                  'max_yaw_rate':np.pi/2}

    df_sur_ekf = [pd.DataFrame()]
    df_sur = df_sur.sort_values(['target_id','time']).set_index('target_id')
    for target_id in df_sur.index.unique():
        df_target = df_sur.loc[target_id].reset_index().copy()
        if len(df_target) < 10:
            continue
        df_target = reconstruct_surrounding(df_target, sur_params.values())
        df_sur_ekf.append(df_target)
    df_sur_ekf = pd.concat(df_sur_ekf)

    return df_sur_ekf

    
    
