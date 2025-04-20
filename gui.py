# gui.py
import json
from datetime import datetime
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from osc_sender import OSCSender
from voice import VoiceRecognizer

class CommandItem(QtWidgets.QListWidgetItem):
    def __init__(self, phrase, actions, enabled=True):
        super().__init__(phrase)
        self.phrase = phrase
        self.actions = actions
        # Make item checkable for enable/disable
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.setCheckState(Qt.Checked if enabled else Qt.Unchecked)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRChat OSC Voice Controller")
        self.resize(600, 500)
        # Dark, futuristic style
        self.setStyleSheet("""
        QWidget {
          background-color: #000;
          color: #fff;
        }
        QLineEdit, QSpinBox, QListWidget, QTextEdit, QTableWidget {
          background-color: #111;
          color: #fff;
        }
        QPushButton {
          background-color: #222;
          color: #fff;
          border: 1px solid #444;
          padding: 5px;
        }
        QPushButton:hover {
          background-color: #333;
        }
        QHeaderView::section {
          background-color: #333;
          color: #fff;
        }
        """
        )
        self._load_settings()
        self._load_commands()
        self._build_ui()
        # Initialize OSC sender and voice recognizer
        self.osc = OSCSender(self.settings["host"], self.settings["port"])
        self.voice = VoiceRecognizer(self.on_phrase_detected)
        self.voice.start()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Host/Port form
        form = QtWidgets.QFormLayout()
        self.host_edit = QtWidgets.QLineEdit(self.settings["host"])
        self.port_edit = QtWidgets.QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(self.settings["port"])
        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_edit)
        save_btn = QtWidgets.QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        form.addRow(save_btn)
        layout.addLayout(form)

        # Commands list
        self.cmd_list = QtWidgets.QListWidget()
        self.cmd_list.itemChanged.connect(self._on_item_toggled)
        layout.addWidget(self.cmd_list)
        self._populate_cmd_list()

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        add_cmd = QtWidgets.QPushButton("Add Command")
        edit_cmd = QtWidgets.QPushButton("Edit Command")
        del_cmd = QtWidgets.QPushButton("Delete Command")
        add_cmd.clicked.connect(self.add_command)
        edit_cmd.clicked.connect(self.edit_command)
        del_cmd.clicked.connect(self.delete_command)
        btn_layout.addWidget(add_cmd)
        btn_layout.addWidget(edit_cmd)
        btn_layout.addWidget(del_cmd)
        layout.addLayout(btn_layout)

        # Log area
        layout.addWidget(QtWidgets.QLabel("Log:"))
        self.log_widget = QtWidgets.QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setFixedHeight(150)
        layout.addWidget(self.log_widget)

    def _load_settings(self):
        try:
            with open("settings.json", "r") as f:
                self.settings = json.load(f)
        except:
            self.settings = {"host": "127.0.0.1", "port": 9000}

    def save_settings(self):
        self.settings["host"] = self.host_edit.text()
        self.settings["port"] = self.port_edit.value()
        with open("settings.json", "w") as f:
            json.dump(self.settings, f, indent=2)
        self.osc = OSCSender(self.settings["host"], self.settings["port"])
        QtWidgets.QMessageBox.information(self, "Saved", "Settings updated.")

    def _load_commands(self):
        try:
            with open("commands.json", "r") as f:
                raw = json.load(f)
        except:
            raw = {"mappings": []}
        # Ensure enabled field exists
        self.command_data = []
        for m in raw.get("mappings", []):
            phrase = m.get("phrase", "+unknown+")
            actions = m.get("actions", [])
            enabled = m.get("enabled", True)
            self.command_data.append({
                "phrase": phrase,
                "actions": actions,
                "enabled": enabled
            })

    def _populate_cmd_list(self):
        self.cmd_list.clear()
        for m in self.command_data:
            item = CommandItem(m["phrase"], m["actions"], m.get("enabled", True))
            self.cmd_list.addItem(item)

    def _save_commands(self):
        data = {"mappings": []}
        for i in range(self.cmd_list.count()):
            item = self.cmd_list.item(i)
            data["mappings"].append({
                "phrase": item.phrase,
                "actions": item.actions,
                "enabled": item.checkState() == Qt.Checked
            })
        with open("commands.json", "w") as f:
            json.dump(data, f, indent=2)

    def add_command(self):
        dlg = AddCommandDialog(self)
        if dlg.exec_():
            phrase, actions = dlg.get_result()
            item = CommandItem(phrase, actions, enabled=True)
            self.cmd_list.addItem(item)
            self._save_commands()

    def edit_command(self):
        selected = self.cmd_list.selectedItems()
        if not selected:
            return
        item = selected[0]
        dlg = AddCommandDialog(self, phrase=item.phrase, actions=item.actions)
        if dlg.exec_():
            phrase, actions = dlg.get_result()
            item.phrase = phrase
            item.actions = actions
            item.setText(phrase)
            self._save_commands()

    def delete_command(self):
        for item in self.cmd_list.selectedItems():
            self.cmd_list.takeItem(self.cmd_list.row(item))
        self._save_commands()

    def _on_item_toggled(self, item):
        state = "enabled" if item.checkState() == Qt.Checked else "disabled"
        self.log(f'Command "{item.phrase}" {state}')
        self._save_commands()

    def on_phrase_detected(self, phrase):
        for i in range(self.cmd_list.count()):
            item = self.cmd_list.item(i)
            if phrase == item.phrase and item.checkState() == Qt.Checked:
                for act in item.actions:
                    self.osc.send(act["path"], act["value"])
                    self.log(f'Executed "{item.phrase}": {act["path"]} = {act["value"]}')

    def log(self, message):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_widget.append(f'[{now}] {message}')

class AddCommandDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, phrase="", actions=None):
        super().__init__(parent)
        self.setWindowTitle("Command Editor")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)
        self.phrase_edit = QtWidgets.QLineEdit(phrase)
        layout.addWidget(QtWidgets.QLabel("Voice Phrase:"))
        layout.addWidget(self.phrase_edit)

        # Actions table
        self.actions_table = QtWidgets.QTableWidget(0, 2)
        self.actions_table.setHorizontalHeaderLabels(["OSC Path", "Value"])
        layout.addWidget(self.actions_table)

        # Pre-populate if editing
        if actions:
            for act in actions:
                row = self.actions_table.rowCount()
                self.actions_table.insertRow(row)
                self.actions_table.setItem(row, 0, QtWidgets.QTableWidgetItem(act.get("path", "")))
                self.actions_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(act.get("value", "0"))) )

        btns = QtWidgets.QHBoxLayout()
        add_act = QtWidgets.QPushButton("Add Action")
        add_act.clicked.connect(self.add_action_row)
        btns.addWidget(add_act)
        layout.addLayout(btns)

        ok_cancel = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        ok_cancel.accepted.connect(self.accept)
        ok_cancel.rejected.connect(self.reject)
        layout.addWidget(ok_cancel)

    def add_action_row(self):
        row = self.actions_table.rowCount()
        self.actions_table.insertRow(row)
        self.actions_table.setItem(row, 0, QtWidgets.QTableWidgetItem("/avatar/parameters/"))
        self.actions_table.setItem(row, 1, QtWidgets.QTableWidgetItem("0"))

    def get_result(self):
        phrase = self.phrase_edit.text().strip().lower()
        actions = []
        for r in range(self.actions_table.rowCount()):
            path = self.actions_table.item(r, 0).text()
            val_str = self.actions_table.item(r, 1).text()
            try:
                val = int(val_str)
            except ValueError:
                val = float(val_str)
            actions.append({"path": path, "value": val})
        return phrase, actions
