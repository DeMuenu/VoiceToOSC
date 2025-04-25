from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QListWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QRadioButton,
    QDialog, QDialogButtonBox, QCompleter, QCheckBox, QListWidgetItem, QButtonGroup
)
from PyQt5.QtGui import QFont, QDoubleValidator

class STT(QDialog):
    def __init__(self,parent=None,activation_phrase="", activate_mode='OFF', confirm_mode='NORMAL'):
        super().__init__(parent)
        self.setWindowTitle("Speech To Chatbox")
        self.resize(400,250)
        self.activate_mode=activate_mode
        self.activation_phrase=activation_phrase
        self.confirm_mode=confirm_mode


        layout=QVBoxLayout(self)


        layout.addWidget(QLabel("Activation Mode:"))

        scope_layout=QHBoxLayout()
        self.off_rb=QRadioButton("OFF")
        self.trigger_rb=QRadioButton("Triggerword")
        self.on_rb=QRadioButton("Always On")
        for rb in (self.off_rb, self.trigger_rb, self.on_rb):
            scope_layout.addWidget(rb)

        self.activate_group = QButtonGroup(self)
        for rb in (self.off_rb, self.trigger_rb, self.on_rb):
            self.activate_group.addButton(rb)
        self.activate_group.setExclusive(True)

        if str(self.activate_mode) == "OFF":
            self.off_rb.setChecked(True)
        if str(self.activate_mode) == "ON":
            self.on_rb.setChecked(True)
        if str(self.activate_mode) == "TRIGGER":
            self.trigger_rb.setChecked(True)

        layout.addLayout(scope_layout)


        layout.addWidget(QLabel("Activation Phrase:"))
        self.phrase_edit=QLineEdit(activation_phrase)
        layout.addWidget(self.phrase_edit)

        layout.addWidget(QLabel("Confirmation Mode:"))
        confirm_layout=QHBoxLayout()

        self.Normal_rb=QRadioButton("No Confirmation")
        self.Confirm_rb=QRadioButton("Needs Confirmation")
        self.Live_rb=QRadioButton("LIVE")
        for rb in (self.Normal_rb, self.Confirm_rb, self.Live_rb):
            confirm_layout.addWidget(rb)
        
        # logical group for exclusivity
        self.confirm_group = QButtonGroup(self)
        for rb in (self.Normal_rb, self.Confirm_rb, self.Live_rb):
            self.confirm_group.addButton(rb)
        self.confirm_group.setExclusive(True)

        #parent.log(self.activate_mode)
        if str(self.confirm_mode) == "NORMAL":
            self.Normal_rb.setChecked(True)
        if str(self.confirm_mode) == "CONFIRM":
            self.Confirm_rb.setChecked(True)
        if str(self.confirm_mode) == "LIVE":
            self.Live_rb.setChecked(True)
        layout.addLayout(confirm_layout)

        ok_cancel=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_cancel.accepted.connect(self.accept); ok_cancel.rejected.connect(self.reject)
        layout.addWidget(ok_cancel)

    def getResult(self):
        if self.off_rb.isChecked():
            self.activate_mode = 'OFF'
        if self.on_rb.isChecked():
            self.activate_mode = 'ON'
        if self.trigger_rb.isChecked():
            self.activate_mode = 'TRIGGER'
        self.activation_phrase = self.phrase_edit.text()

        if self.Normal_rb.isChecked():
            self.confirm_mode = 'NORMAL'
        if self.Confirm_rb.isChecked():
            self.confirm_mode = 'CONFIRM'
        if self.Live_rb.isChecked():
            self.confirm_mode = 'LIVE'

        return self.activation_phrase, self.activate_mode, self.confirm_mode