'''
This script contains functions to reconstruct the ego vehicle and
surrounding vehicles using Extended Kalman Filter (EKF).
'''
import numpy as np


# Reconstruct the trajectory of the ego/subject vehicle
# Extended Kalman Filter for Constant Heading and Acceleration,
# adapted from https://github.com/balzer82/Kalman/blob/master/Extended-Kalman-Filter-CTRA.ipynb
def reconstruct_ego(df_ego, params=[], reverse=False):
    if len(params)==0:
        uncertainty_init=100.
        uncertainty_speed=100.
        uncertainty_omega=10.
        uncertainty_acc=10.
        max_jerk=0.5
        max_yaw_rate=0.1
        max_acc=9.8
        max_yaw_acc=1.
    else:
        uncertainty_init, uncertainty_speed, uncertainty_omega, uncertainty_acc, max_jerk, max_yaw_rate, max_acc, max_yaw_acc = params

    veh = df_ego.sort_values('time').copy().reset_index(drop=True)
    if reverse:
        veh = veh.iloc[::-1].reset_index(drop=True)

    ## Constants
    g = 9.81  ### gravity, m/s^2
    mph2mps = 0.44704  ### mph to m/s
    
    ## Convert yaw rate to radians per second
    veh['yaw_rate'] = np.deg2rad(veh['yaw_rate'])
    ## Convert acceleration to m/s^2
    veh['acc_lat'] = veh['acc_lat'] * g
    veh['acc_lon'] = veh['acc_lon'] * g
    ## Convert speed to m/s
    veh['speed_comp'] = veh['speed_comp']*mph2mps

    ## Initialize
    numstates = 6
    P = np.eye(numstates)*uncertainty_init # Initial Uncertainty
    R = np.diag([uncertainty_speed,uncertainty_omega,uncertainty_acc]) # Measurement Noise
    I = np.eye(numstates)
    dt = np.gradient(veh['time'])
    acc_square = (veh['acc_lat']**2+veh['acc_lon']**2).values
    Trigger = (acc_square>0.).astype('bool') # Perform EKF when acceleration is not zero

    ## Measurement vector
    mv = veh['speed_comp'].values
    momega = veh['yaw_rate'].values
    momega[(momega<1e-6)&(momega>=0)] = 1e-6
    momega[(momega>-1e-6)&(momega<0)] = -1e-6
    macc = veh['acc_lon'].values
    measurements = np.vstack((mv,momega,macc))
    m = measurements.shape[1] 

    ## Initial state
    x = np.array([0,0,0,mv[0],momega[0],macc[0]])

    ## Estimated vector
    estimates = np.zeros((m,numstates))
    estimates[0,:] = x

    for filterstep in np.arange(1,m):
        ## Time Update (Prediction)
        x[0] = x[0] + (1/x[4]**2) * (-x[3]*x[4]*np.sin(x[2]) -x[5]*np.cos(x[2]) +
                                     x[5]*np.cos(x[2]+x[4]*dt[filterstep]) + 
                                     (x[5]*x[4]*dt[filterstep]+x[3]*x[4])*np.sin(x[2]+x[4]*dt[filterstep]))
        x[1] = x[1] + (1/x[4]**2) * (x[3]*x[4]*np.cos(x[2]) - x[5]*np.sin(x[2]) +
                                     x[5]*np.sin(x[2]+x[4]*dt[filterstep]) +
                                     (-x[5]*x[4]*dt[filterstep]-x[3]*x[4])*np.cos(x[2]+x[4]*dt[filterstep]))
        x[2] = (x[2] + x[4] * dt[filterstep] + np.pi) % (2.0 * np.pi) - np.pi
        x[3] = x[3] + x[5] * dt[filterstep]
        x[4] = x[4]
        x[5] = x[5]

        ## Calculate the Jacobian of the Dynamic Matrix JA
        a13 = (-x[4]*x[3]*np.cos(x[2]) + x[5]*np.sin(x[2]) - x[5]*np.sin(dt[filterstep]*x[4]+x[2]) +
               (dt[filterstep]*x[4]*x[5]+x[4]*x[3])*np.cos(dt[filterstep]*x[4]+x[2])) / x[4]**2
        a14 = (-x[4]*np.sin(x[2]) + x[4]*np.sin(dt[filterstep]*x[4]+x[2])) / x[4]**2
        a15 = (-dt[filterstep]*x[5]*np.sin(dt[filterstep]*x[4]+x[2]) + 
               dt[filterstep]*(dt[filterstep]*x[4]*x[5]+x[4]*x[3])*np.cos(dt[filterstep]*x[4]+x[2]) - 
               x[3]*np.sin(x[2]) + (dt[filterstep]*x[5] + x[3])*np.sin(dt[filterstep]*x[4]+x[2]))/x[4]**2 - (
                   -x[4]*x[3]*np.sin(x[2]) - x[5]*np.cos(x[2]) +
                   x[5]*np.cos(dt[filterstep]*x[4] + x[2]) + 
                   (dt[filterstep]*x[4]*x[5] + x[4]*x[3])*np.sin(dt[filterstep]*x[4] + x[2])) *2 / x[4]**3
        a16 = (dt[filterstep]*x[4]*np.sin(dt[filterstep]*x[4]+x[2]) - np.cos(x[2]) + np.cos(dt[filterstep]*x[4]+x[2])) / x[4]**2

        a23 = (-x[4]*x[3]*np.sin(x[2]) - x[5]*np.cos(x[2]) + x[5]*np.cos(dt[filterstep]*x[4]+x[2]) -
               (-dt[filterstep]*x[4]*x[5] - x[4]*x[3])*np.sin(dt[filterstep]*x[4]+x[2])) / x[4]**2
        a24 = (x[4]*np.cos(x[2]) - x[4]*np.cos(dt[filterstep]*x[4] + x[2])) / x[4]**2
        a25 = (dt[filterstep]*x[5]*np.cos(dt[filterstep]*x[4] + x[2]) -
               dt[filterstep]*(-dt[filterstep]*x[4]*x[5]-x[4]*x[3])*np.sin(dt[filterstep]*x[4]+x[2]) + 
               x[3]*np.cos(x[2]) + (-dt[filterstep]*x[5]-x[3])*np.cos(dt[filterstep]*x[4]+x[2]))/x[4]**2 - (
                   x[4]*x[3]*np.cos(x[2]) - x[5]*np.sin(x[2]) + 
                   x[5]*np.sin(dt[filterstep]*x[4]+x[2]) +
                   (-dt[filterstep]*x[4]*x[5]-x[4]*x[3])*np.cos(dt[filterstep]*x[4]+x[2])) *2 / x[4]**3
        a26 =  (-dt[filterstep]*x[4]*np.cos(dt[filterstep]*x[4]+x[2]) - np.sin(x[2]) + np.sin(dt[filterstep]*x[4] + x[2])) / x[4]**2
            
        JA = np.matrix([[1.0, 0.0, a13, a14, a15, a16],
                        [0.0, 1.0, a23, a24, a25, a26],
                        [0.0, 0.0, 1.0, 0.0, dt[filterstep], 0.0],
                        [0.0, 0.0, 0.0, 1.0, 0.0, dt[filterstep]],
                        [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]], dtype=float)

        ## Calculate the Process Noise Covariance Matrix
        s_pos = 0.5*max_acc*dt[filterstep]**2
        s_psi = max_yaw_rate*dt[filterstep]
        s_speed = max_acc*dt[filterstep]
        s_omega = max_yaw_acc*dt[filterstep]
        s_acc = max_jerk*dt[filterstep]

        Q = np.diag([s_pos**2, s_pos**2, s_psi**2, s_speed**2, s_omega**2, s_acc**2])

        ## Project the error covariance ahead
        P = JA*P*JA.T + Q

        ## Measurement Update (Correction)
        hx = np.matrix([[x[3]],[x[4]],[x[5]]])

        if Trigger[filterstep]:
            JH = np.matrix([[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]], dtype=float)
        else:
            JH = np.matrix([[0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], dtype=float)        

        S = JH*P*JH.T + R
        K = (P*JH.T) * np.linalg.inv(S.astype('float'))

        ## Update the estimate
        Z = measurements[:,filterstep].reshape(JH.shape[0],1)
        y = Z - (hx)  ### Innovation or Residual

        ## Check if the measurement is invalid
        ### 1) the speed measurement is -1
        ### 2) the speed measurement drops to 0 although the vehile is accelerating
        if mv[filterstep]<0. or (mv[filterstep]<=0. and macc[filterstep-1:filterstep+2].mean()>0.):
            y[0] = 0.
        x = x + np.array(K*y).reshape(-1)

        ## Limit the speed to be non-negative
        if x[3]<0:
            x[3] = 0.

        ## Update the error covariance
        P = (I - (K*JH))*P

        ## Save states
        estimates[filterstep,:] = x

    veh[['x_ekf','y_ekf','psi_ekf','v_ekf','omega_ekf','acc_ekf']] = estimates
    if reverse:
        veh = veh.iloc[::-1].reset_index(drop=True)

    return veh



# Reconstruct the trajectory of the surrounding vehicles
# Extended Kalman Filter for Constant Heading and Velocity
# Adapted from https://github.com/balzer82/Kalman/blob/master/Extended-Kalman-Filter-CHCV.ipynb
def reconstruct_surrounding(veh, params=[]):
    if len(params)==0:
        uncertainty_init=100.
        uncertainty_pos=50.
        uncertainty_speed=10.
        max_acc=9.8
        max_yaw_rate=np.pi/2
    else:
        uncertainty_init, uncertainty_pos, uncertainty_speed, max_acc, max_yaw_rate = params
    
    ## Initialize
    numstates = 4
    P = np.eye(numstates)*uncertainty_init # Initial Uncertainty
    dt = np.gradient(veh['time'])
    R = np.diag([uncertainty_pos,uncertainty_pos,uncertainty_speed]) # Measurement Noise
    I = np.eye(numstates)
    mx, my, mv = veh['x'].values, veh['y'].values, veh['speed_comp'].values
    Trigger = (mv>0.).astype('bool') # Perform EKF when speed is not zero

    ## Measurement vector
    measurements = np.vstack((mx, my, mv))
    m = measurements.shape[1]

    ## Initial state
    x = np.array([mx[0], my[0], mv[0], 0.])

    ## Estimated vector
    estimates = np.zeros((m,4))

    for filterstep in range(m):
        ## Time Update (Prediction)
        x[0] = x[0] + dt[filterstep]*x[2]*np.cos(x[3])
        x[1] = x[1] + dt[filterstep]*x[2]*np.sin(x[3])
        x[2] = x[2]
        x[3] = (x[3]+ np.pi) % (2.0*np.pi) - np.pi

        ## Calculate the Jacobian of the Dynamic Matrix JA
        a13 = dt[filterstep]*np.cos(x[3])
        a14 = -dt[filterstep]*x[2]*np.sin(x[3])
        a23 = dt[filterstep]*np.sin(x[3])
        a24 = dt[filterstep]*x[2]*np.cos(x[3])
        JA = np.matrix([[1.0, 0.0, a13, a14],
                        [0.0, 1.0, a23, a24],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0]], dtype=float)

        ## Calculate the Process Noise Covariance Matrix
        s_pos = 0.5*max_acc*dt[filterstep]**2
        s_psi = max_yaw_rate*dt[filterstep]
        s_speed = max_acc*dt[filterstep]

        Q = np.diag([s_pos**2, s_pos**2, s_speed**2, s_psi**2])

        ## Project the error covariance ahead
        P = JA*P*JA.T + Q

        ## Measurement Update (Correction)
        hx = np.matrix([[x[0]],[x[1]],[x[2]]])

        if Trigger[filterstep]:
            JH = np.matrix([[1.0, 0.0, 0.0, 0.0],
                            [0.0, 1.0, 0.0, 0.0],
                            [0.0, 0.0, 1.0, 0.0]], dtype=float)
        else:
            JH = np.matrix([[0.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 0.0, 0.0]], dtype=float)        

        S = JH*P*JH.T + R
        K = (P*JH.T) * np.linalg.inv(S.astype('float'))

        ## Update the estimate
        Z = measurements[:,filterstep].reshape(JH.shape[0],1)
        y = Z - (hx)                         # Innovation or Residual
        x = x + np.array(K*y).reshape(-1)

        ## Update the error covariance
        P = (I - (K*JH))*P

        ## Save states
        estimates[filterstep,:] = x

    veh[['x_ekf','y_ekf','v_ekf','psi_ekf']] = estimates

    return veh
