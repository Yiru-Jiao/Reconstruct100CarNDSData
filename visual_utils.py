'''
This script contains functions for visualization.
'''

import matplotlib.pyplot as plt
plt.rcParams.update({'font.size': 8})
from matplotlib.patches import Rectangle
from matplotlib import colors
from matplotlib.collections import PatchCollection
import numpy as np
from IPython.display import display, clear_output
import time as systime


class RotateRectangle(Rectangle): # adapted from a Stack Overflow answer https://stackoverflow.com/a/60413175
    def __init__(self, xy, width, length, rotate_ref_x, rotate_ref_y, **kwargs):
        super().__init__(xy, width, length, **kwargs)
        self.rel_point_of_rot = np.array([rotate_ref_x, rotate_ref_y])
        self.xy_center = self.get_xy()
        self.set_angle(self.angle)

    def _apply_rotation(self):
        angle_rad = self.angle * np.pi / 180
        m_trans = np.array([[np.cos(angle_rad), -np.sin(angle_rad)],
                            [np.sin(angle_rad), np.cos(angle_rad)]])
        shift = -m_trans @ self.rel_point_of_rot
        self.set_xy(self.xy_center + shift)

    def set_angle(self, angle):
        self.angle = angle
        self._apply_rotation()

    def set_xy_center(self, xy):
        self.xy_center = xy
        self._apply_rotation()
        

def rgb_color(colorname, alpha=1.):
    color = colors.to_rgb(colorname)
    return (color[0], color[1], color[2], alpha)


def draw_single_veh(ax, veh, color, rotate_ref_x, rotate_ref_y, ekf=True, annotate=False):
    patches = []
    hx, hy = np.cos(veh['psi_ekf']), np.sin(veh['psi_ekf'])
    angle = np.arctan2(hy, hx) * 180 / np.pi - 90
    if ekf:
        x, y = veh['x_ekf'], veh['y_ekf']
    else:
        x, y = veh['x'], veh['y']
    if annotate:
        ax.text(x, y, str(veh['target_id']), fontsize=10)
    patches.append(RotateRectangle((x, y), 1.8, 4.5, rotate_ref_x, rotate_ref_y, angle=angle))
    ax.add_collection(PatchCollection(patches, color=color, alpha=0.6))
    return ax


def draw_events(ax, event_t, rotate_ref_x, rotate_ref_y, annotate=False):
    event_t = event_t.copy()
    event_t['hx_i'] = np.cos(event_t['psi_i'])
    event_t['hy_i'] = np.sin(event_t['psi_i'])
    event_t['hx_j'] = np.cos(event_t['psi_j'])
    event_t['hy_j'] = np.sin(event_t['psi_j'])
    for vehid, color, ref_x, ref_y in zip(['_i','_j'],['r','b'],[1/2, rotate_ref_x],[1/2, rotate_ref_y]):
        x, y, hx, hy = event_t[['x'+vehid, 'y'+vehid, 'hx'+vehid, 'hy'+vehid]].values[0]
        width, length = event_t[['width'+vehid, 'length'+vehid]].values[0]
        angle = np.arctan2(hy, hx) * 180 / np.pi - 90
        patches = [(RotateRectangle((x, y), width, length, width*ref_x, length*ref_y, angle=angle))]
        ax.add_collection(PatchCollection(patches, color=color, alpha=0.6))
    if annotate:
        ax.text(x, y, str(event_t['target_id'].values[0]))
    return ax


def visualize_trip(df_ego, df_sur, trip_id):
    xlim = [min(df_ego['x_ekf'].min(), df_sur['x_ekf'].min())-5, 
            max(df_ego['x_ekf'].max(), df_sur['x_ekf'].max())+5]
    ylim = [min(df_ego['y_ekf'].min(), df_sur['y_ekf'].min())-5, 
            max(df_ego['y_ekf'].max(), df_sur['y_ekf'].max())+5]

    for t in df_ego['time'].values:
        dt_ego = df_ego[df_ego['time'] == t]
        dtpast_ego = df_ego[(df_ego['time']<=t)&(df_ego['time']>=t-1)]
        dt_sur = df_sur[df_sur['time'] == t]
        dtpast_sur = df_sur[(df_sur['time']<=t)&(df_sur['time']>=t-1)]

        fig, ax = plt.subplots(1, 1, figsize=(10, 5), dpi=200)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.set_title('Trip: %d, Time: %.1f' % (trip_id, t))
        ax = draw_single_veh(ax, dt_ego.iloc[0], 'red', 1.8/2, 4.5/2, annotate=False)
        ax.plot(dtpast_ego['x_ekf'], dtpast_ego['y_ekf'], 'g', alpha=0.5)

        for i in range(len(dt_sur)):
            ax.plot(dtpast_sur[dtpast_sur['target_id']==dt_sur.iloc[i]['target_id']]['x_ekf'],
                    dtpast_sur[dtpast_sur['target_id']==dt_sur.iloc[i]['target_id']]['y_ekf'], 'g', alpha=0.5)

        s = 5*((ax.get_window_extent().width/(xlim[1]-xlim[0])*72./fig.dpi)**2)
        ax.scatter(dt_sur['x_ekf'], dt_sur['y_ekf'], c='blue', s=s, alpha=0.5)

        display(fig)
        systime.sleep(0.02)
        clear_output(wait=True)
        plt.close(fig)


def visualize_event(events, trip_id, save=False, save_dir='./'):
    xlim = [min(events['x_i'].min(), events['x_j'].min()), 
            max(events['x_i'].max(), events['x_j'].max())]
    addition = (100 - (xlim[1] - xlim[0]))/2
    if (xlim[1] - xlim[0])<100:
        xlim = [xlim[0]-addition, xlim[1]+addition]
    ylim = [min(events['y_i'].min(), events['y_j'].min())-5,
            max(events['y_i'].max(), events['y_j'].max())+5]

    for t in events['time'].values:
        event_t = events[events['time']==t]
        event_past = events[(events['time']<=t)&(events['time']>=t-1)]

        fig, ax = plt.subplots(1, 1, figsize=(10, 5), dpi=200)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect('equal')
        ax.set_title('Trip: %d, Time: %.1f, Event: %d' % (trip_id, t, event_t['event'].values[0]))
        
        if event_t['forward'].values[0]:
            ref_x, ref_y = 1/2, 0.
        else:
            ref_x, ref_y = 1/2, 1.
        ax = draw_events(ax, event_t, ref_x, ref_y)
        ax.plot(event_past['x_i'], event_past['y_i'], 'g', alpha=0.5)
        ax.plot(event_past['x_j'], event_past['y_j'], 'g', alpha=0.5)

        if save:
            fig.savefig(save_dir+f'frame_{int(round(t,2)*100)}.png', bbox_inches='tight', dpi=400)
            plt.close(fig)
        else:
            display(fig)
            systime.sleep(0.01)
            clear_output(wait=True)
            plt.close(fig)
