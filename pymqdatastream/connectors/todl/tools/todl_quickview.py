import sys
import argparse
import numpy as np
import pylab as pl
import netCDF4
import logging
import pymqdatastream.connectors.todl.todl_data_processing as todl_data_processing

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except:
    from qtpy import QtCore, QtGui, QtWidgets

#https://matplotlib.org/3.1.0/gallery/user_interfaces/embedding_in_qt_sgskip.html
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
if is_pyqt5():
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
else:
    from matplotlib.backends.backend_qt4agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('todl_quickview')
logger.setLevel(logging.DEBUG)

# FP07 Polynom hack
T = np.asarray([1.4, 9.01, 20.96, 27.55,34.77])
V = np.asarray([2.95, 2.221, 1.508, 1.26, 1.07])

P = np.polyfit(V,T,2)
#print('Polynom',P)



#https://stackoverflow.com/questions/18539679/embedding-the-matplotlib-toolbar-in-pyqt4-using-matplotlib-custom-widget#18563884
class MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()       
        self.ax = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self,
        QtWidgets.QSizePolicy.Expanding,
        QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        
class MplWidget(QtWidgets.QWidget):
     def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.vbl = QtWidgets.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.vbl.addWidget(self.mpl_toolbar)
        self.setLayout(self.vbl)


class todlquickviewMainWindow(QtWidgets.QMainWindow):
    """The main interface of the TODL-Quickview gui

    """
    def __init__(self,fname):
        QtWidgets.QMainWindow.__init__(self)
        self.all_widgets = []
        mainMenu = self.menuBar()
        self.setWindowTitle("TODL Quickview")
        #self.setWindowIcon(QtGui.QIcon('logo/pymqdatastream_logo_v0.2.svg.png'))
        extractAction = QtWidgets.QAction("&Quit", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Closing the program')
        extractAction.triggered.connect(self.close_application)

        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)

        self.statusBar()

        self.mainwidget = todlquickviewWidget(fname)
        self.setCentralWidget(self.mainwidget)                
        self.width_orig = self.frameGeometry().width()
        self.height_orig = self.frameGeometry().height()
        self.width_main = self.width_orig
        self.height_main = self.height_orig
    def close_application(self):
        logger.debug('Goodbye!')
        self.close()
        for w in self.mainwidget.plotWidgets:
            w.close()
            
        self.mainwidget.close()
        

class todlquickviewWidget(QtWidgets.QWidget):
    """
    """
    def __init__(self,fname=None):
        QtWidgets.QMainWindow.__init__(self)
        layout = QtWidgets.QGridLayout()
        self.plotWidgets = []
        self.data = {}
        self.layout = layout
        self.setLayout(layout)
        
        self.plot_button = QtWidgets.QPushButton('Plot')
        self.plot_button.clicked.connect(self.plot_data)
        self.var_combo = QtWidgets.QComboBox(self)

        self.layout.addWidget(self.var_combo,0,0)
        self.layout.addWidget(self.plot_button,0,1)
        
        if(fname is not None):
            logger.debug('Opening file:' + fname)
            self.read_ncfile(fname)

            

        self.show()

    def plot_data(self):
        print('Plotting')
        plotvar_y = self.var_combo.currentText()
        plotdata_y = self.data[plotvar_y][plotvar_y][:]
        plotdata_x = self.data[plotvar_y]['x0'][:]
        try:
            lab_unit = '[' + self.data[plotvar_y][plotvar_y].units + ']'
        except:
            lab_unit = ''
        ylabel = plotvar_y + lab_unit
        if('ch1' in plotvar_y):
            print('Calculating temperature from polynom')
            plotdata_y = np.polyval(P,plotdata_y)
            plotdata_y = np.ma.masked_where((plotdata_y > T.max()) | (plotdata_y < T.min()),plotdata_y)
            #print(T.max(),T.min())

        
        # Calculate the frequency
        fi = 1/(np.diff(plotdata_x).mean())
        plotFrame = MplWidget()
        ax = plotFrame.canvas.ax
        plotFrame.canvas.ax.plot(plotdata_x,plotdata_y)
        ax.set_title('Frequency:' + str(fi))
        ax.set_xlabel('t [s]')
        ax.set_ylabel(ylabel)        
        plotFrame.show()
        self.plotWidgets.append(plotFrame)

    def read_ncfile(self,fname):
        nc = netCDF4.Dataset(fname)
        # Try to read ADC data
        try:    
            nca = nc.groups['adc']
        except:
            nca = None
            pass

        if(nca is not None):
            for varname in nca.variables:
                vartmp = nca.variables[varname]
                print(vartmp)
                print(vartmp.dimensions[0])
                if(not "cnt" in varname):
                    self.data[vartmp.name] = {vartmp.name:vartmp,vartmp.dimensions[0]:nca.variables[vartmp.dimensions[0]]}
                    self.data[vartmp.name]['x0'] = self.data[vartmp.name][vartmp.dimensions[0]]
                    # Add to the gui
                    self.var_combo.addItem(varname)
                    #self.FLAG_CH1=True
                    #print('Found ch1 ADC data')                                
                else:
                    print('cnt ...')
                    


        # Read in PyroScience data
        print('Trying Firesting data')
        try:
            ncp = nc.groups['pyro']
            cnt10ks_p = ncp.variables['cnt10ks_pyro'][:]
            #time_p = netCDF4.num2date(ncp.variables['time'][:],units = ncp.variables['time'].units)
            fp = 1/(np.diff(cnt10ks_p).mean())
            # Add to the gui                
            self.var_combo.addItem('phi')
            #phi = ncp.variables['phi'][:]
            # Add to the data
            self.data['phi'] = {'phi':ncp.variables['phi'],'cnt10ks_p':ncp.variables['cnt10ks_pyro']}
            self.data['phi']['x0'] = self.data['phi']['cnt10ks_p']                
            self.FLAG_PYRO=True
            print('Found Pyro data')        
        except Exception as e:
            print('Pyro:' + str(e))
            self.FLAG_PYRO=False


        # Read in IMU
        print('Trying IMU data')        
        try:
            self.FLAG_IMU = True        
            nci = nc.groups['imu']
            cnt10ks_imu = nci.variables['cnt10ks_imu'][:]
            #time_imu = netCDF4.num2date(nci.variables['time'][:],units=nci.variables['time'].units)        
            fi = 1/(np.diff(cnt10ks_imu).mean())
            for vartmp in nci.variables:
                print(vartmp)
                if(not "cnt" in vartmp):
                    print('reading')
                    self.var_combo.addItem(vartmp)
                    self.data[vartmp] = {vartmp:nci.variables[vartmp],'cnt10ks_imu':nci.variables['cnt10ks_imu']}
                    self.data[vartmp]['x0'] = self.data[vartmp]['cnt10ks_imu']
                    
            #accx = nci.variables['accx'][:]
            #accy = nci.variables['accy'][:]
            #accz = nci.variables['accz'][:]
            #gyrox = nci.variables['gyrox'][:]
            #gyroy = nci.variables['gyroy'][:]
            #gyroz = nci.variables['gyroz'][:]
            #magx = nci.variables['magx'][:]
            #magy = nci.variables['magy'][:]
            #magz = nci.variables['magz'][:]
            print('Found IMU data')                
        except Exception as e:
            print('Hallo!')
            print(e)
            self.FLAG_IMU = False








        



# If run from the command line
def main():
    print('This is todl_quickview')
    app = QtWidgets.QApplication(sys.argv)
    screen_resolution = app.desktop().screenGeometry()
    width, height = screen_resolution.width(), screen_resolution.height()
    if(len(sys.argv) > 1):
        fname = sys.argv[1]
    else:
        print('Specify a file for quickview')
        exit()
        
    window = todlquickviewMainWindow(fname=fname)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main_gui()        

