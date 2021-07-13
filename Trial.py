# -*- coding: utf-8 -*-
"""
Created on Fri Jun 25 22:46:37 2021

@author: 218019067
"""

import csv
import math
import numpy as np
from matplotlib import pyplot as plt
from USVmodel import USVmodel


class Trial: 
    # one single trial of experiment
    def __init__(self, path):
        # get the extension information
        self.extension = int(path.split("/")[3].split("_")[1])
        #print(self.extension)
        # get the pwm command
        self.PWM = [int(i) for i in path.split("/")[6].split("_")[1::2]]
        #print(self.PWM)
        # get all data
        self.readCSV(path)
    
    def readCSV(self, file_path):
        # read csv files to obtain the initial state and the time list
        header = 7 # jump the header
        deque_length = 10 # jump the first data
        skip_sec = 1 # skip the first 1 second
        # get_initial_state_flag = False # whether the initial state obtained
        #
        self.t_lst = []
        
        self.x_lst = []
        self.y_lst = []
        self.w_lst = []
        
        self.velx_lst = []
        self.vely_lst = []
        self.velw_lst = []
        
        self.state_deque = []
        
        with open(file_path, newline='') as csv_f:
            f_reader = csv.reader(csv_f)
            row_i = 0 # count which row
            data_i = 0 # count which data
            for row in f_reader:
                row_i += 1
                
                # skip the headers
                if row_i <= header:
                    continue
                
                # skip the empty row
                if row[2] == '':
                    continue
                
                data_i += 1 # all next are data
                
                # prepare data
                t = eval(row[1])
                x, y, w = self.getXYW(row)
                
                # skip the first 10 data
                if data_i <= deque_length:
                    self.state_deque.append([t, x, y, w])
                    continue
                
                # calculate the speed for every 10 data
                self.state_deque.append([t, x, y, w])
                #print(self.state_deque)
                delta_t = self.state_deque[-1][0] - self.state_deque[0][0]
                vel_x = (self.state_deque[-1][1] - self.state_deque[0][1])/delta_t
                vel_y = (self.state_deque[-1][2] - self.state_deque[0][2])/delta_t
                vel_w = (self.state_deque[-1][3] - self.state_deque[0][3])/delta_t
                self.state_deque.pop(0)
                
            #    if not get_initial_state_flag:
            #        # calculate the speed for every 10 data
            #        if data_i == 1:
            #            init_x, init_y, init_w = x, y, w
            #            t_last = t
            #        elif data_i % 10 == 1:
            #            delta_t = t - t_last
            #            vel_x = (x-init_x)/delta_t
            #            vel_y = (y-init_y)/delta_t
            #            vel_w = (w-init_w)/delta_t
            #            init_x = x
            #            init_y = y
            #            init_w = w
            #            t_last = t
                    
                # skip the first second
                if t <= skip_sec: 
                    continue
                
                t, x, y, w = self.state_deque[int(deque_length/2)]
                # for after the first second
                self.t_lst.append(t)
                self.x_lst.append(x)
                self.y_lst.append(y)
                self.w_lst.append(w)
                self.velx_lst.append(vel_x)
                self.vely_lst.append(vel_y)
                self.velw_lst.append(vel_w)
                
            #    if not get_initial_state_flag:
            #        get_initial_state_flag = True
            #        self.initial_state.append(x)
            #        self.initial_state.append(y)
            #        self.initial_state.append(w)
            #        self.initial_state.append(vel_x)
            #        self.initial_state.append(vel_y)
            #        self.initial_state.append(vel_w)           
        # x, y, w, velx, vely, velw
        self.initial_state = [self.x_lst[0], self.y_lst[0], self.w_lst[0],
                              self.velx_lst[0], self.vely_lst[0], self.velw_lst[0]] 
        #print(self.t_lst)
        #print(self.initial_state)
    
    def QuaternionToEuler(self, intput_data, angle_is_rad = True):
        # change angle vale to radian if False
    
        w = intput_data[0] 
        y = intput_data[1]    # x
        z = intput_data[2]    # y
        x = intput_data[3]    # z
    
        r = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        p = math.asin(2 * (w * y - z * x))
        y = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    
        if not angle_is_rad: # pi -> 180
    
            r = r / math.pi * 180
            p = p / math.pi * 180
            y = y / math.pi * 180
    
        return [r,p,y]
    
    def getXYW(self, row):
        qx1, qy1, qz1, qw1 = eval(row[2]), eval(row[3]), eval(row[4]), eval(row[5])
        q1 = [qw1, qx1, qy1, qz1]
        w =  self.QuaternionToEuler(q1)[2]
        x = eval(row[8])
        y = eval(row[6])
        return x, y, w
    
    def InertvToBodyv(self, inertial_v, w):
        # inertial_v is a list
        R = np.array([[math.cos(w), -math.sin(w), 0],
                    [math.sin(w), math.cos(w), 0],
                    [0, 0, 1]])
        inertial_v = np.transpose(np.array(inertial_v))
        body_v = np.matmul(np.linalg.inv(R), inertial_v)
        return body_v.tolist() # return a list
    
    def setParameters(self, parameters):
        # m1, m2, m3, d1, d2, d3
        self.mass = parameters[0:3]
        self.drag = parameters[3:6]
        
    def setErrorWeight(self, w):
        self.errorWeight = np.diag(np.array(w))
    
    def errorCalculation(self, Ve, Vs, W):
        # Ve is the 2D experimental velocity
        # Vs is the 2D simulation velocity
        # W is the weight
        if len(Ve) == len(Vs):
            error = np.array([])
            for ve, vs in zip(Ve, Vs):
                e = np.array([i - j for i,j in zip(ve,vs)])
                error = np.append(error, np.dot(np.dot(e, W), e.T))
            
            return error.sum()
        else:
            print("Wrong velocity dimension!")
            return 0
    
    def trial(self, w = [1,1,1]): 
        # new a USVmodel
        init_vel = self.InertvToBodyv(self.initial_state[3:6], self.initial_state[2])
        USV = USVmodel(self.initial_state[0:3], init_vel, self.extension)    
        
        # set parameter
        USV.setMass(self.mass)
        USV.setDrag(self.drag)
        USV.pwmToPropulsion(self.PWM)

        # simulation
        last_t = self.t_lst[0]
        for t in self.t_lst[1:]:
            delta_t = t - last_t
            USV.update(delta_t)
            last_t = t
        
        # prepare data
        Vel_exp = [[i,j,k] for i,j,k in zip(self.velx_lst, self.vely_lst, self.velw_lst)]
        Vel_sim = USV.state_history[:, 3:6].tolist()
        self.x_sim_lst = USV.state_history[:, 0].tolist()
        self.y_sim_lst = USV.state_history[:, 1].tolist()
        self.w_sim_lst = USV.state_history[:, 2].tolist()
        self.setErrorWeight(w)
        self.error = self.errorCalculation(Vel_exp, Vel_sim, self.errorWeight)
        #print(self.error)
        #
        #print(USV.state_history)
    
    def drawArrow(self, x, y, w, scale, color):
        # scale = 0.01
        dx = np.cos(w) * scale
        dy = np.sin(w) * scale
        plt.arrow(x, y, dx, dy, 
                width=0.01*scale, head_width=0.2*scale, head_length=0.1*scale, 
                shape="full",
                fc=color, ec=color)
    
    def showFigures(self):
        plt.text(self.initial_state[0], self.initial_state[1], "Origin")
        # draw Arrow
        arrow_scale = 0.001
        x_span = np.max(self.x_lst) - np.min(self.x_lst)
        y_span = np.max(self.y_lst) - np.min(self.y_lst)
        arrow_scale *= np.min([x_span, y_span])
        
        L = len(self.t_lst)
        for i in range(L):
            self.drawArrow(self.x_lst[i], self.y_lst[i], self.w_lst[i], arrow_scale, "b")
            self.drawArrow(self.x_sim_lst[i], self.y_sim_lst[i], self.w_sim_lst[i],
                            arrow_scale, "r")
            
        plt.plot(self.x_lst, self.y_lst, label="Experiment")
        plt.plot(self.x_sim_lst, self.y_sim_lst, label="Simulation")
        plt.legend()
        plt.show()
        
# Test script
if __name__ == "__main__":
    # directories
    root_dir = "./Data/USV/"
    ext_dir = ["Extension_0/", "Extension_10/", "Extension_20/", "Extension_30/", "Extension_40/", "Extension_50/"]
    exp_type_dir = ["Circle/", "Spinning/", "StraightLine/"]
    c_set_dir = ["Anticlockwise/", "Clockwise/"]
    l_set_dir = ["Backward/", "Forward/", "Leftward/", "Rightward/"]
    exp_name = "PWM1_0_PWM2_110_PWM3_0_PWM4_110/"
    file_name = "Take 2021-06-13 06.40.43 PM_013.csv"
    
    # entity the simulation
    trial = Trial(root_dir + ext_dir[0] + exp_type_dir[2] + l_set_dir[0] + exp_name + file_name)
    
    #OASES.setMass(2, 1, 1.2)
    #OASES.setDrag(0.02, 0.01, 0.02)
    
    #
    #sim.expFiles()
    #sim.readCSV(sim.files[0])
    # trial.setParameters([40, 40, 12, 2, 2, 2])
    trial.setParameters([30, 60, 150, 50, 40, 60])
    trial.trial()
    print(trial.error)
    trial.showFigures()
    