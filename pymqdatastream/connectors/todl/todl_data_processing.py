import numpy as np

def findspikes(t,x,dxdt):
    """Searching for spikes in a TODL LTC2442 data series. The algorithm
searches for the given threshold. If it is found and the subsequent
data exceeds the threshold as well with a negative sign its defined as
a spike

    Args:
        t: time 
        x: data
        dxdt: Threshold for rejection, a working rejection for FP07 is 0.1 [V/s]

    """
    #print('Despiking')
    dt = np.diff(t)
    dx = np.diff(x)
    spikes = np.zeros(np.shape(t))
    for i in range(1,len(dt)-1):
        dxdt1 = dx[i]/dt[i]
        dxdt2 = dx[i+1]/dt[i+1]
        if(abs(dxdt1) > dxdt):
            if(abs(dxdt1) > dxdt):
                if(np.sign(dxdt1) == -np.sign(dxdt2)):
                    spikes[i+1] = 1
                    
    #print('Done despiking')
    return spikes
