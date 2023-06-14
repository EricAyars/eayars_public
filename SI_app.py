#! /usr/bin/env python
'''
    SoApp.py
    Eric Ayars
    6/15/22

    A Python solution to Monica So's need for solar cell testing

    The way this works:
        There are functions that define what to do when controls are pressed.
        There is a bit of code that draws the controls and puts it on the
            window in the right places.
        Then the program just sits there until something happens.
            If the start button is pressed, it does start_clicked(), for example.
        This version is for the Keithley 2401 SourceMeter, which does sweeps automatically.

    1/3/23: added front/rear port option to GUI.
'''


# constants
MaxN = 1000                     # max number of data points before a crash!
minV = 0.0                      # minimum voltage
maxV = 2.0                      # maximum voltage

########################################
#
#   The import list
#
########################################

import sys                      # useful system calls

import numpy as np              # arrays, etc.

# VISA stuff for communication with DMM
import pyvisa

# GUI stuff
from PyQt5.QtWidgets import (
    QApplication, 
    QWidget, 
    QPushButton, 
    QVBoxLayout, 
    QHBoxLayout, 
    QFileDialog,
    QComboBox,
    QLabel,
    QLineEdit
)
from PyQt5.QtGui import QDoubleValidator

#from PyQt5.QtCore import QTimer

# plotting package bits
import matplotlib as mpl
mpl.use('QT5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# plotting OOP stuff stolen from 
# https://www.learnpyqt.com/courses/graphics-plotting/plotting-matplotlib/
class MPLCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MPLCanvas, self).__init__(fig)

########################################
#
#   Variables
#
########################################

# global variables
N = 100                         # Number of data points
SM = None
meterSelected = False           # Is the DMM selected?
Imax = 0.0                      # maximum current seen
Imax_index = 0                  # index for Imax
IVmax = 0.0                     # Maximum area
IVmax_index = 0                 # index for maximum area
zero_index = 0                  # array index for I=0
Vmax = 0.0                      # Voltage for I=0
fillFactor = 0.0                # IVmax / (Imax*Vmax)
efficiency = 0.0                # IVmax * area / flux power density
area = 2.76                     # sample area (cm^2?)
flux = 100.0                    # mW/cm^2

########################################
#
#   event-handlers
#
########################################

def start_clicked():
    # This collects the data, returns it as a string.
    # the string elements are voltage and current pairs, CSV.

    # disable start button
    startButton.setDisabled(True)
    # enable stop button
    stopButton.setDisabled(False)
    SM.write("output on")
    datastring = SM.query("read?")
    SM.write("output off")
    processData(datastring)
    startButton.setDisabled(False)

def stop_clicked():
    # for emergency use only!
    # disable stop button
    stopButton.setDisabled(True)
    # enable start button
    startButton.setDisabled(False)
    # disconnect power
    SM.write("output off")

def save_clicked():
    # this needs help still.
    # open datafile
    filename, _ = QFileDialog.getSaveFileName()
    file = open(filename, 'w')
    # write file header
    file.write("# Area = %0.5f (units?)\n" % area)
    file.write("# Flux = %0.5f (units?)\n" % flux)
    file.write("# Max Current = %0.5f mA\n" % Imax)
    file.write("# Max Voltage = %0.5f V\n" % Vmax)
    file.write("# Fill Factor = %0.3f \n" % fillFactor)
    file.write("# Efficiency = %0.3f\n" % efficiency)
    file.write("# Voltage\tCurrent\n")
    # write all data (up to N)
    for j in range(N):
        file.write("%0.5f\t%0.5g\n" % (voltage[j], current[j]))
    # close file
    file.close()
    # update save button text and availability
    saveButton.setText("Data Saved")
    saveButton.setDisabled(True)

def selectionChange():
    # change sourcemeter interface 
    global SM 
    SM = rm.open_resource(selectMenu.currentText())
    SM.timeout = 30000  # 30 second timeout on communications, to allow sweeps without timeout error
    SM.write("syst:beep 440") # concert A to let us know we found the meter
    # Configure meter for sweep
    SM.write("route:term front")
    SM.write("source:function:mode volt")
    SM.write("source:volt:start %0.2f" % minV)
    SM.write("source:volt:stop %0.2f" % maxV)
    SM.write("source:volt:mode sweep")
    SM.write("format:elements voltage, current")
    SM.write("source:sweep:points %d" % N)
    SM.write("trig:count %d" % N)
    meterSelected = True
    if meterSelected:
        portMenu.setDisabled(False)
        startButton.setDisabled(False)
        startVentry.setDisabled(False)
        stopVentry.setDisabled(False)
        fluxEntry.setDisabled(False)
        areaEntry.setDisabled(False)

def areaSet():
    # Numeric value of area has been set
    global area
    area = float(areaEntry.text())

def fluxSet():
    # numeric value of flux has been set
    global flux 
    flux = float(fluxEntry.text())

def portSet():
    # connects to either front or rear port on meter
    port = portMenu.currentText()
    SM.write("route:term %s" % port)

########################################
#
#   Non-interface functions
#
########################################

def processData(dataString):
    # converts the string of data from CSV into useful arrays.
    # creates a graph, updates key values.
    global voltage
    global current
    global scene
    global zero_index
    global Imax
    global Imax_index
    global IVmax
    global IVmax_index
    global Vmax
    global fillFactor
    global efficiency
    global area
    global flux

    zero = 0.00001  # Current less than this should be considered zero?

    # split data on commas, put it into arrays.
    data=dataString.split(',')
    voltage = np.array([float(data[j]) for j in range(0,2*N,2) ])
    current = np.array([float(data[j]) for j in range(1,2*N,2) ])

    # set up analysis here, once Monica figures out what should be analyzed and how!

    # clear the graph
    scene.axes.cla()

    # redraw the graph
    scene.axes.plot(voltage,current*1000, 'r.')
    scene.axes.set_xlabel("Voltage (V)")
    scene.axes.set_ylabel("Current (mA)")

    # show the graph
    scene.draw()

    # turn on save-data button
    saveButton.setDisabled(False)

def minVset():
    global minV
    minV = float(startVentry.text())
    SM.write("source:volt:start %0.2f" % minV)

def maxVset():
    global maxV
    maxV = float(stopVentry.text())
    SM.write("source:volt:stop %0.2f" % maxV)

def updateOutput():
    ffOutput.setText("Fill Factor: %0.2f  " % fillFactor)
    efOutput.setText("Efficiency: %0.2f " % efficiency)

########################################
#
# Main program
#
########################################

current = np.zeros(N)
voltage = np.zeros(N)

app = QApplication(sys.argv)
widget = QWidget()

#
# Interface and parameter selections
#

selections = QHBoxLayout()

# Check available VISA resources
rm = pyvisa.ResourceManager()
devices = rm.list_resources()
ports = ('Front', 'Rear')
port = 'Front'

# Sourcemeter interface (SM) selection drop-down
selectMenu = QComboBox(widget)
selectMenu.addItem('Sourcemeter')
selectMenu.addItems(devices)
selectMenu.currentIndexChanged.connect(selectionChange)

# port selection drop-down
portMenu = QComboBox(widget)
portMenu.addItems(ports)
portMenu.setDisabled(True)
portMenu.currentIndexChanged.connect(portSet)

# put drop-downs in the selection box
selections.addWidget(selectMenu)
selections.addWidget(portMenu)
selections.addStretch(1)

# voltage start/stop points
voltages = QHBoxLayout()

# min V text-box
startVlabel = QLabel(widget)
startVlabel.setText("Start Voltage (V)")
startVentry = QLineEdit()
startVentry.setValidator(QDoubleValidator(-5,5,2))
startVentry.setText("%0.2f" % minV)
startVentry.setDisabled(True)
startVentry.editingFinished.connect(minVset)

# max V text-box
stopVlabel = QLabel(widget)
stopVlabel.setText("Stop Voltage (V)")
stopVentry = QLineEdit()
stopVentry.setValidator(QDoubleValidator(-5,5,2))
stopVentry.setText("%0.2f" % maxV)
stopVentry.setDisabled(True)
stopVentry.editingFinished.connect(maxVset)

# put voltages in the voltages box
voltages.addWidget(startVlabel)
voltages.addWidget(startVentry)
voltages.addWidget(stopVlabel)
voltages.addWidget(stopVentry)
voltages.addStretch(1)

# Area and flux parameters
parameters = QHBoxLayout()

# area text-box
areaLabel = QLabel(widget)
areaLabel.setText("Sample Area (cm^2)")
areaEntry = QLineEdit()
areaEntry.setMaxLength(10)
areaEntry.setText("%0.5f" % area)
areaEntry.setDisabled(True)
areaEntry.textChanged.connect(areaSet)

# flux text-box
fluxLabel = QLabel(widget)
fluxLabel.setText("Flux (mW/cm^2)")
fluxEntry = QLineEdit()
fluxEntry.setMaxLength(10)
fluxEntry.setText("%0.5f" % flux)
fluxEntry.setDisabled(True)
fluxEntry.textChanged.connect(fluxSet)

# put parameters in the parameter box
parameters.addWidget(areaLabel)
parameters.addWidget(areaEntry)
parameters.addWidget(fluxLabel)
parameters.addWidget(fluxEntry)
parameters.addStretch(1)

#
# Control buttons
#

controls = QHBoxLayout()

# start
startButton = QPushButton(widget)
startButton.setText("Start")
startButton.setDisabled(True)
startButton.clicked.connect(start_clicked)

# stop
stopButton = QPushButton(widget)
stopButton.setText("Stop")
stopButton.clicked.connect(stop_clicked)
stopButton.setDisabled(True)

# save
saveButton = QPushButton(widget)
saveButton.setText("Save Data")
saveButton.clicked.connect(save_clicked)
saveButton.setDisabled(True)

# put buttons in the container
controls.addWidget(startButton)
controls.addWidget(stopButton)
controls.addWidget(saveButton)
controls.addStretch(1)

#
# scene (graph)
# 

# graph
scene = MPLCanvas(width=5, height=4, dpi=100)
# The next 2 lines don't work yet, fix when online.
#scene.axes.xlabel("Voltage (V)")
#scene.axes.ylabel("Current (mA)")

# graph toolbar
toolbar = NavigationToolbar2QT(scene, widget)

#
#   results
#

results = QHBoxLayout()

ffOutput = QLabel(widget)
efOutput = QLabel(widget)
updateOutput()
results.addWidget(ffOutput)
results.addWidget(efOutput)
results.addStretch(1)

#
# window layout
#

layout = QVBoxLayout()
layout.addLayout(selections)
layout.addLayout(voltages)
layout.addLayout(parameters)
layout.addLayout(controls)
layout.addWidget(toolbar)
layout.addWidget(scene)
layout.addLayout(results)

# Draw the screen
widget.setLayout(layout)
widget.setWindowTitle("Solar cell tester")
widget.show()

sys.exit(app.exec_())
