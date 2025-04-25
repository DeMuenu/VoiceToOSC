from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QListWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QRadioButton,
    QDialog, QDialogButtonBox, QCompleter, QCheckBox, QListWidgetItem
)
from PyQt5.QtGui import QFont, QDoubleValidator

class STT(QDialog):
    def __init__(self,parent=None,activation_phrase="", activate_mode='OFF'):
        super().__init__(parent)
        self.setWindowTitle("Speech To Chatbox")
        self.resize(400,250)
        self.activate_mode=activate_mode
        self.activation_phrase=activation_phrase
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("Voice Phrase:"))
        scope_layout=QHBoxLayout()
        self.off_rb=QRadioButton("OFF")
        self.trigger_rb=QRadioButton("Triggerword")
        self.on_rb=QRadioButton("Always On")

        scope_layout.addWidget(self.off_rb); scope_layout.addWidget(self.trigger_rb); scope_layout.addWidget(self.on_rb)
        parent.log(self.activate_mode)
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

        return self.activation_phrase, self.activate_mode