# gui.py
import os
import json
import threading
from datetime import datetime
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QListWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QRadioButton,
    QDialog, QDialogButtonBox
)
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from osc_sender import OSCSender
from voice import VoiceRecognizer

class CommandItem(QtWidgets.QListWidgetItem):
    def __init__(self, phrase, actions, enabled=True, scope='global'):
        super().__init__(phrase)
        self.phrase = phrase
        self.actions = actions
        self.scope = scope
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.setCheckState(Qt.Checked if enabled else Qt.Unchecked)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VRChat OSC Voice Controller")
        self.resize(700, 600)
        self.setStyleSheet("""
            QWidget { background-color: #000; color: #fff; }
            QLineEdit, QSpinBox, QListWidget, QTextEdit, QTableWidget { background-color: #111; color: #fff; }
            QPushButton { background-color: #222; color: #fff; border: 1px solid #444; padding: 5px; }
            QPushButton:hover { background-color: #333; }
            QHeaderView::section { background-color: #333; color: #fff; }
        """)

        # State
        self.available_params = []
        self.current_avatar_id = None
        self.listening = False

        # Load settings & commands
        self._load_settings()
        self._load_commands()

        # Build UI
        self._build_ui()

        # OSC sender & voice
        self.osc = OSCSender(self.settings['host'], self.settings['out_port'])
        self.voice = VoiceRecognizer(self.on_phrase_detected)

        # Start OSC listener
        self._start_osc_listener()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Settings
        form = QFormLayout()
        self.host_edit = QLineEdit(self.settings['host'])
        self.out_port_edit = QSpinBox(); self.out_port_edit.setRange(1,65535); self.out_port_edit.setValue(self.settings['out_port'])
        self.in_port_edit = QSpinBox(); self.in_port_edit.setRange(1,65535); self.in_port_edit.setValue(self.settings['in_port'])
        form.addRow("Outgoing Host:", self.host_edit)
        form.addRow("Outgoing Port:", self.out_port_edit)
        form.addRow("Incoming Port:", self.in_port_edit)
        btns = QHBoxLayout()
        save_btn = QPushButton("Save Settings"); save_btn.clicked.connect(self.save_settings)
        self.toggle_btn = QPushButton("Start Listening"); self.toggle_btn.clicked.connect(self.toggle_listening)
        btns.addWidget(save_btn); btns.addWidget(self.toggle_btn)
        form.addRow(btns)
        layout.addLayout(form)

        # Commands list
        self.cmd_list = QListWidget(); self.cmd_list.itemChanged.connect(self._on_item_toggled)
        layout.addWidget(self.cmd_list)
        self._populate_cmd_list()

        # Command controls
        ctrl = QHBoxLayout()
        add_btn = QPushButton("Add Command"); add_btn.clicked.connect(self.add_command)
        edit_btn = QPushButton("Edit Command"); edit_btn.clicked.connect(self.edit_command)
        del_btn = QPushButton("Delete Command"); del_btn.clicked.connect(self.delete_command)
        ctrl.addWidget(add_btn); ctrl.addWidget(edit_btn); ctrl.addWidget(del_btn)
        layout.addLayout(ctrl)

        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_widget = QTextEdit(); self.log_widget.setReadOnly(True); self.log_widget.setFixedHeight(160)
        layout.addWidget(self.log_widget)

    def toggle_listening(self):
        if self.listening:
            self.voice.stop(); self.listening=False; self.toggle_btn.setText("Start Listening"); self.log("Voice listening stopped")
        else:
            self.voice.start(); self.listening=True; self.toggle_btn.setText("Stop Listening"); self.log("Voice listening started")

    def _load_settings(self):
        try:
            with open('settings.json') as f: self.settings=json.load(f)
        except: self.settings={'host':'127.0.0.1','out_port':9000,'in_port':9001}
        self.settings.setdefault('out_port',self.settings.get('port',9000))
        self.settings.setdefault('in_port',9001)

    def save_settings(self):
        self.settings['host']=self.host_edit.text(); self.settings['out_port']=self.out_port_edit.value(); self.settings['in_port']=self.in_port_edit.value()
        with open('settings.json','w') as f: json.dump(self.settings,f,indent=2)
        self.osc=OSCSender(self.settings['host'],self.settings['out_port'])
        self.log(f"Settings saved: out {self.settings['host']}:{self.settings['out_port']}, in {self.settings['in_port']}")
        QtWidgets.QMessageBox.information(self,'Saved','Settings updated.')

    def _load_commands(self):
        try:
            with open('commands.json') as f: raw=json.load(f)
        except: raw={'mappings':[]}
        self.command_data=[{
            'phrase':m.get('phrase',''),
            'actions':m.get('actions',[]),
            'enabled':m.get('enabled',True),
            'scope':m.get('scope','global')
        } for m in raw.get('mappings',[])]

    def _populate_cmd_list(self):
        self.cmd_list.clear()
        for cmd in self.command_data:
            if cmd['scope']=='global' or cmd['scope']==self.current_avatar_id:
                self.cmd_list.addItem(CommandItem(cmd['phrase'],cmd['actions'],cmd['enabled'],cmd['scope']))

    def _save_commands(self):
        data={'mappings':[]}
        for i in range(self.cmd_list.count()):
            it=self.cmd_list.item(i)
            data['mappings'].append({
                'phrase':it.phrase,'actions':it.actions,
                'enabled':it.checkState()==Qt.Checked,'scope':it.scope
            })
        with open('commands.json','w') as f: json.dump(data,f,indent=2)

    def _start_osc_listener(self):
        disp=Dispatcher(); disp.map('/avatar/change',self._on_avatar_change)
        addr=('0.0.0.0',self.settings['in_port'])
        try:
            server=osc_server.ThreadingOSCUDPServer(addr,disp)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.log(f"OSC listener on port {self.settings['in_port']}")
        except Exception as e:
            self.log(f"Listener error: {e}")

    def _on_avatar_change(self,unused,avatar_id):
        self.current_avatar_id=avatar_id; self.log(f"Avatar change detected: {avatar_id}")
        self._auto_load_avatar_config(avatar_id); self._populate_cmd_list()

    def _auto_load_avatar_config(self,avatar_id):
        root=os.path.join(os.path.expanduser('~'),'AppData','LocalLow','VRChat','VRChat','OSC')
        try:
            users=[d for d in os.listdir(root) if d.startswith('usr_')]
            users.sort(key=lambda u:os.path.getmtime(os.path.join(root,u)),reverse=True)
            cfg=os.path.join(root,users[0],'Avatars',f'{avatar_id}.json')
            self.log(f"Loading avatar config: {cfg}")
            if not os.path.isfile(cfg): raise FileNotFoundError(cfg)
            txt=open(cfg).read().strip()
            if not txt: raise ValueError("Empty file")
            data=json.loads(txt)
            params=[]
            for p in data.get('parameters',[]):
                inp=p.get('input',{}); out=p.get('output',{})
                if 'address' in inp: params.append(inp['address'])
                if 'address' in out: params.append(out['address'])
            self.available_params=params; self.log(f"Loaded {len(params)} params")
        except Exception as e:
            self.log(f"Auto-load failed: {e}")

    def add_command(self):
        dlg=AddCommandDialog(self,available_params=self.available_params,current_avatar=self.current_avatar_id)
        if dlg.exec_():
            phrase,acts,scope=dlg.get_result();
            self.command_data.append({'phrase':phrase,'actions':acts,'enabled':True,'scope':scope})
            self._populate_cmd_list(); self._save_commands()

    def edit_command(self):
        sel=self.cmd_list.selectedItems()
        if not sel: return
        it=sel[0]
        dlg=AddCommandDialog(self,phrase=it.phrase,actions=it.actions,available_params=self.available_params,current_avatar=self.current_avatar_id,initial_scope=it.scope)
        if dlg.exec_():
            phrase,acts,scope=dlg.get_result()
            for cmd in self.command_data:
                if cmd['phrase']==it.phrase and cmd['scope']==it.scope:
                    cmd.update({'phrase':phrase,'actions':acts,'scope':scope}); break
            self._populate_cmd_list(); self._save_commands()

    def delete_command(self):
        sel=self.cmd_list.selectedItems()
        for it in sel:
            self.command_data=[c for c in self.command_data if not(c['phrase']==it.phrase and c['scope']==it.scope)]
        self._populate_cmd_list(); self._save_commands()

    def _on_item_toggled(self,it):
        for cmd in self.command_data:
            if cmd['phrase']==it.phrase and cmd['scope']==it.scope:
                cmd['enabled']=(it.checkState()==Qt.Checked); break
        self.log(f"Command '{it.phrase}' {'enabled' if it.checkState()==Qt.Checked else 'disabled'}")
        self._save_commands()

    def on_phrase_detected(self,phrase):
        for cmd in self.command_data:
            if cmd['enabled'] and phrase==cmd['phrase'] and (cmd['scope']=='global' or cmd['scope']==self.current_avatar_id):
                for act in cmd['actions']:
                    self.osc.send(act['path'],act['value']); #self.log(f"Executed '{cmd['phrase']}': {act['path']} = {act['value']}')

    def log(self,msg):
        t=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_widget.append(f'[{t}] {msg}')

class AddCommandDialog(QDialog):
    def __init__(self,parent=None,phrase="",actions=None,available_params=None,current_avatar=None,initial_scope='global'):
        super().__init__(parent)
        self.setWindowTitle("Command Editor")
        self.resize(550,380)
        self.available_params=available_params or []
        self.current_avatar=current_avatar
        self.initial_scope=initial_scope
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("Voice Phrase:"))
        self.phrase_edit=QLineEdit(phrase)
        layout.addWidget(self.phrase_edit)
        scope_layout=QHBoxLayout()
        self.global_rb=QRadioButton("Global")
        self.avatar_rb=QRadioButton("Avatar-specific")
        scope_layout.addWidget(self.global_rb); scope_layout.addWidget(self.avatar_rb)
        layout.addLayout(scope_layout)
        if self.current_avatar:
            self.avatar_rb.setEnabled(True)
            if self.initial_scope==self.current_avatar: self.avatar_rb.setChecked(True)
            else: self.global_rb.setChecked(True)
        else:
            self.avatar_rb.setEnabled(False); self.global_rb.setChecked(True)
        self.actions_table=QTableWidget(0,2)
        self.actions_table.setHorizontalHeaderLabels(["OSC Path","Value"])
        self.actions_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        layout.addWidget(self.actions_table)
        if actions:
            for act in actions: self.add_action_row(act.get('path',''),str(act.get('value','0')))
        btns=QHBoxLayout()
        add_btn=QPushButton("Add Action"); add_btn.clicked.connect(self.add_action_row)
        btns.addWidget(add_btn); layout.addLayout(btns)
        ok_cancel=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_cancel.accepted.connect(self.accept); ok_cancel.rejected.connect(self.reject)
        layout.addWidget(ok_cancel)
    def add_action_row(self,path="",value="0"):
        r=self.actions_table.rowCount(); self.actions_table.insertRow(r)
        combo=QComboBox(); combo.setEditable(True); combo.addItems(self.available_params); combo.setCurrentText(path)
        self.actions_table.setCellWidget(r,0,combo); self.actions_table.setItem(r,1,QTableWidgetItem(value))
    def get_result(self):
        phrase=self.phrase_edit.text().strip().lower()
        scope='global' if self.global_rb.isChecked() else self.current_avatar
        actions=[]
        for r in range(self.actions_table.rowCount()):
            w=self.actions_table.cellWidget(r,0)
            path=w.currentText().strip() if w else (self.actions_table.item(r,0).text().strip() if self.actions_table.item(r,0) else '')
            val_it=self.actions_table.item(r,1)
            vs=val_it.text().strip() if val_it else ''
            try: v=int(vs)
            except: 
                try: v=float(vs)
                except: v=0
            if path: actions.append({'path':path,'value':v})
        return phrase,actions,scope