# gui.py
import os
import json
import threading
from datetime import datetime
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QUrl
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QListWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QRadioButton,
    QDialog, QDialogButtonBox, QCompleter, QCheckBox, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QFont, QDoubleValidator, QDesktopServices
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
from osc_sender import OSCSender
from voice import VoiceRecognizer
import sounddevice as sd
import urllib.request

GITHUB_API_LATEST = "https://api.github.com/repos/DeMuenu/VoiceToOSC/releases/latest"
CURRENT_VERSION = "0.0.3"
CHECK_DELAY_MS   = 1000



def parse_version(v):
    parts = []
    for part in v.split('.'):
        num = ''
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            parts.append(int(num))
        else:
            parts.append(0)
    return parts

def is_newer(latest, current):
    a = parse_version(latest)
    b = parse_version(current)
    # pad the shorter list
    n = max(len(a), len(b))
    a += [0] * (n - len(a))
    b += [0] * (n - len(b))
    return a > b  # lexicographic comparison

from modules.speechtotext import STT

class CommandItem(QtWidgets.QListWidgetItem):
    def __init__(self, phrase, actions, enabled=True, scope='global'):
        super().__init__(phrase)
        self.phrase = phrase
        self.actions = actions
        self.scope = scope
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.setCheckState(Qt.Checked if enabled else Qt.Unchecked)

class MainWindow(QMainWindow):
    avatarChanged = pyqtSignal(str)
    avatarLoaded  = pyqtSignal(str)
    logSignal = pyqtSignal(str)
    scheduleOSC = pyqtSignal(str, object, float)

    def __init__(self):
        super().__init__()
        self.avatarChanged.connect(self._on_avatar_change_main)
        self.avatarLoaded .connect(self._on_avatar_loaded_main)
        self.logSignal.connect(self._append_log)
        self.scheduleOSC.connect(self._on_schedule_osc)
        self.setWindowTitle("VRChat VoiceToOSC")
        self.resize(1000, 700)
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
        self.param_values = {}


        # Load settings & commands
        self._load_settings()
        self._load_commands()
        self._load_module_settings()

        # Build UI

        self._build_ui()


        #check for app updates
        QTimer.singleShot(CHECK_DELAY_MS, self.check_for_updates)

        # OSC sender & voice
        self.osc = OSCSender(self.settings['host'], self.settings['out_port'])
        self.voice = VoiceRecognizer(self.on_phrase_detected, model_path=self.settings['model_path'], device=self.settings.get('device'))

        # Start OSC listener
        self._start_osc_listener()
        self.toggle_listening()

    def check_for_updates(self):
        req = urllib.request.Request(
        GITHUB_API_LATEST,
        headers={"User-Agent": "VoiceUpdater/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            # silently ignore or log
            print(f"Update check failed: {e}")
            return

        tag = data.get("tag_name", "")
        latest = tag.lstrip("v")  # e.g. "v1.2.3" → "1.2.3"
        if is_newer(latest, CURRENT_VERSION):
            notes  = data.get("body", "").strip()
            assets = data.get("assets", [])
            download_url = data.get("html_url")  # fallback
            for asset in assets:
                name = asset.get("name", "")
                if name.endswith(".exe") or name.endswith(".msi"):
                    download_url = asset["browser_download_url"]
                    break
            self.prompt_update(tag, notes, download_url)

    def prompt_update(self, tag, notes, url):
        html_notes = notes.replace('\n', '<br>')
        msg = (f"A new version <b>{tag}</b> is available!<br><br>"
               f"<b>Release notes:</b><br>{html_notes[:500]}…<br><br>"
               f"Would you like to update?")
        reply = QMessageBox.question(
            self, "Update Available", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            QDesktopServices.openUrl(QUrl(url))


    def _emit_avatar_changed(self, addr, avatar_id):
        self.avatarChanged.emit(avatar_id)

    def _emit_avatar_loaded(self, addr, avatar_id_str):
        self.avatarLoaded.emit(avatar_id_str)

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


        #model selection
        self.model_box = QComboBox()
        # Populate with any sub‑folders in ./models/
        for name in sorted(os.listdir('models')):
            full = os.path.join('models', name)
            if os.path.isdir(full):
                self.model_box.addItem(name, full)
        # select saved path
        saved = self.settings['model_path']
        idx = self.model_box.findData(saved)
        if idx >= 0:
            self.model_box.setCurrentIndex(idx)
        form.addRow("Vosk Model:", self.model_box)


        self.device_box = QComboBox()
        self._refresh_device_list()
        form.addRow("Input Device:", self.device_box)
        save_btn = QPushButton("Save Settings"); save_btn.clicked.connect(self.save_settings)
        self.toggle_btn = QPushButton("Start Listening"); self.toggle_btn.clicked.connect(self.toggle_listening)
        btns.addWidget(save_btn); btns.addWidget(self.toggle_btn)
        form.addRow(btns)
        




        layout.addLayout(form)


        #Warning
        
        self.Warning_label = QLabel("Waiting for an Avatar to load...")
        # Style the background
        layout.addWidget(self.Warning_label)
        font = QFont()
        font.setPointSize(20)            # 20 pt font
        font.setBold(True)  
        self.Warning_label.setStyleSheet("background-color: yellow; color: black;")
        self.Warning_label.setFont(font)

        # Commands list
        self.cmd_list = QListWidget()
        layout.addWidget(self.cmd_list)
        self._populate_cmd_list()

        # Command controls
        ctrl = QHBoxLayout()
        add_btn = QPushButton("Add Command"); add_btn.clicked.connect(self.add_command)
        edit_btn = QPushButton("Edit Command"); edit_btn.clicked.connect(self.edit_command)
        del_btn = QPushButton("Delete Command"); del_btn.clicked.connect(self.delete_command)
        ctrl.addWidget(add_btn); ctrl.addWidget(edit_btn); ctrl.addWidget(del_btn)
        layout.addLayout(ctrl)

        #features
        modules = QHBoxLayout()
        stt_btn = QPushButton("Speech to Chatbox"); stt_btn.clicked.connect(self.edit_stt)
        modules.addWidget(stt_btn)
        layout.addLayout(modules)

        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_widget = QTextEdit(); self.log_widget.setReadOnly(True); self.log_widget.setFixedHeight(160)
        layout.addWidget(self.log_widget)


    def remove_Warning(self):
        if self.Warning_label is not None:
            layout = self.centralWidget().layout()
            # Remove it from the layout...
            layout.removeWidget(self.Warning_label)
            # ...schedule it for deletion...
            self.Warning_label.deleteLater()
            # ...and clear our reference
            self.Warning_label = None

    
    def _refresh_device_list(self):
        self.device_box.clear()
        devices = sd.query_devices()
        # show only inputs
        inputs = [(i, d['name']) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        for idx, name in inputs:
            self.device_box.addItem(f"{idx}: {name}", idx)
        # select saved
        saved = self.settings.get('device')
        if saved is not None and 0 <= saved < len(devices):
            for i in range(self.device_box.count()):
                if self.device_box.itemData(i) == saved:
                    self.device_box.setCurrentIndex(i)
                    break

    def toggle_listening(self):
        if self.listening:
            self.voice.stop(); self.listening=False; self.toggle_btn.setText("Start Listening"); self.log("Voice listening stopped")
        else:
            self.voice.start(); self.listening=True; self.toggle_btn.setText("Stop Listening"); self.log("Voice listening started")

    def _load_module_settings(self):
        try:
            with open('module_settings.json') as f: self.module_settings=json.load(f)
        except: self.module_settings={'stt_mode':'OFF','stt_activation__phrase':'status'}
        self.module_settings.setdefault('stt_mode', 'OFF')
        self.module_settings.setdefault('stt_activation__phrase','status')

    def _save_module_settings(self):
        with open('module_settings.json','w') as f: json.dump(self.module_settings,f,indent=2)

    def _load_settings(self):
        try:
            with open('settings.json') as f: self.settings=json.load(f)
        except: self.settings={'host':'127.0.0.1','out_port':9000,'in_port':9001}
        self.settings.setdefault('out_port',self.settings.get('port',9000))
        self.settings.setdefault('in_port',9001)
        self.settings.setdefault('model_path', 'models/vosk-model-small-en-us-0.15')

    def save_settings(self):
        self.settings['host']=self.host_edit.text(); self.settings['out_port']=self.out_port_edit.value(); self.settings['in_port']=self.in_port_edit.value(); self.settings['device'] = self.device_box.currentData(); self.settings['model_path'] = self.model_box.currentData() 
        with open('settings.json','w') as f: json.dump(self.settings,f,indent=2)
        self.osc=OSCSender(self.settings['host'],self.settings['out_port'])
        self.log(f"Settings saved: out {self.settings['host']}:{self.settings['out_port']}, in {self.settings['in_port']}")
        
        if self.listening:
            self.voice.stop()
        self.voice = VoiceRecognizer(self.on_phrase_detected, model_path=self.settings['model_path'], device=self.settings['device'])
        if self.listening:
            self.voice.start()


        QtWidgets.QMessageBox.information(self,'Saved','Settings updated.')

    def _load_commands(self):
        try:
            with open('commands.json') as f: raw=json.load(f)
        except: raw={'mappings':[]}
        self.command_data=[{
            'phrase':m.get('phrase',''),
            'actions':m.get('actions',[]),
            'enabled':m.get('enabled',True),
            'scope':m.get('scope','global'),
            'in_sentence': m.get('in_sentence', False)
        } for m in raw.get('mappings',[])]

    def _populate_cmd_list(self):
        self.cmd_list.clear()
        for cmd in self.command_data:
            if cmd['scope']=='global' or cmd['scope']==self.current_avatar_id:
                item = QListWidgetItem(self.cmd_list)
                widget = CommandListItemWidget(cmd, main_win=self, parent=self.cmd_list)
                item.setSizeHint(widget.sizeHint())
                self.cmd_list.setItemWidget(item, widget)

    def _save_commands(self):
        data = {'mappings': []}
        for cmd in self.command_data:
            data['mappings'].append({
                'phrase': cmd['phrase'],
                'actions': cmd['actions'],
                'enabled':  cmd['enabled'],
                'scope':    cmd['scope'],
                'in_sentence': cmd['in_sentence']
            })
        with open('commands.json', 'w') as f:
            json.dump(data, f, indent=2)

    

    def _start_osc_listener(self):
        disp = Dispatcher()
        disp.map('/avatar/change', self._emit_avatar_changed)
        disp.map('/avatar/parameters/name', self._emit_avatar_loaded)
        disp.map('/avatar/parameters/*',   self._on_param_changed)

        addr=('0.0.0.0',self.settings['in_port'])
        try:
            server=osc_server.ThreadingOSCUDPServer(addr,disp)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            self.log(f"OSC listener on port {self.settings['in_port']}")
        except Exception as e:
            self.log(f"Listener error: {e}")


    def _on_param_changed(self, unused_addr, value):
        # store every incoming parameter value by its OSC path
        self.param_values[unused_addr] = value


    def _on_avatar_change(self,unused,avatar_id):
        self.current_avatar_id=avatar_id; self.log(f"Avatar change detected: {avatar_id}")
        self._auto_load_avatar_config(avatar_id); self._populate_cmd_list()

    def _on_avatar_loaded(self, unused_addr, avatar_id_str):

        # Store the avatar ID
        self.current_avatar_id = avatar_id_str
        self.log(f"Avatar loaded via OSC param: {avatar_id_str}")

        # Load its OSC config (populates self.available_params)
        self._auto_load_avatar_config(avatar_id_str)

        # Refresh the command list to show any avatar‑specific commands
        self._populate_cmd_list()


    @pyqtSlot(str)
    def _on_avatar_change_main(self, avatar_id):
        self.current_avatar_id = avatar_id
        self.log(f"Avatar change detected: {avatar_id}")
        self._auto_load_avatar_config(avatar_id)
        self._populate_cmd_list()

    @pyqtSlot(str)
    def _on_avatar_loaded_main(self, avatar_id_str):
        self.current_avatar_id = avatar_id_str
        self.log(f"Avatar loaded via OSC param: {avatar_id_str}")
        self._auto_load_avatar_config(avatar_id_str)
        self._populate_cmd_list()

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
            raw = open(cfg, 'rb').read()               # read as bytes
            print(repr(raw[:10]))                       # dump the first few bytes
            txt = raw.decode('utf‑8-sig', errors='replace') # or try 'utf‑8‑sig'
            data = json.loads(txt)
            params = []
            for p in data.get('parameters', []):
                inp = p.get('input', {})
                if 'address' in inp:
            # save both address and declared type
                    params.append({'address': inp['address'], 'type':    inp.get('type','Float')
            })
            self.available_params = params
            self.remove_Warning()
        except Exception as e:
            self.log(f"Auto-load failed: {e}")

    def add_command(self):
        dlg=AddCommandDialog(self,available_params=self.available_params,current_avatar=self.current_avatar_id)
        if dlg.exec_():
            phrase, acts, scope = dlg.get_result()
            self.command_data.append({
            'phrase':       phrase,
            'actions':      acts,
            'enabled':      True,
            'scope':        scope,
            'in_sentence':  False
            })
            self._populate_cmd_list()
            self._save_commands()

    def edit_command(self):
        sel = self.cmd_list.selectedItems()
        if not sel:
            return
        item   = sel[0]
        widget = self.cmd_list.itemWidget(item)
        cmd    = widget.cmd
        dlg = AddCommandDialog(
            self,
            phrase=cmd['phrase'],
            actions=cmd['actions'],
            available_params=self.available_params,
            current_avatar=self.current_avatar_id,
            initial_scope=cmd['scope']
        )
        if dlg.exec_():
            new_phrase, new_actions, new_scope = dlg.get_result()
            cmd['phrase']  = new_phrase
            cmd['actions'] = new_actions
            cmd['scope']   = new_scope

            # refresh the list so labels and scopes update
            self._populate_cmd_list()
            self._save_commands()

    def delete_command(self):
        sel_items = self.cmd_list.selectedItems()
        if not sel_items:
            return

        # Build a set of (phrase, scope) tuples to delete
        to_delete = {
            (self.cmd_list.itemWidget(item).cmd['phrase'],
            self.cmd_list.itemWidget(item).cmd['scope'])
            for item in sel_items
        }

        # Filter out any commands matching those tuples
        self.command_data = [
            c for c in self.command_data
            if (c['phrase'], c['scope']) not in to_delete
        ]

        # Refresh the UI and save
        self._populate_cmd_list()
        self._save_commands()

    def edit_stt(self):
            dlg=STT(self,activation_phrase=self.module_settings['stt_activation__phrase'], activate_mode=self.module_settings['stt_mode'])
            if dlg.exec_():
                self.module_settings['stt_activation__phrase'], self.module_settings['stt_mode'] = dlg.getResult()
                self.log(f"Set stt_activation__phrase to: {self.module_settings['stt_activation__phrase']}. Set stt_mode to: {self.module_settings['stt_mode']}.")
                self._save_module_settings()

    def _on_item_toggled(self,it):
        for cmd in self.command_data:
            if cmd['phrase']==it.phrase and cmd['scope']==it.scope:
                cmd['enabled']=(it.checkState()==Qt.Checked); break
        self.log(f"Command '{it.phrase}' {'enabled' if it.checkState()==Qt.Checked else 'disabled'}")
        self._save_commands()

    def _set_in_sentence(self, cmd, checked):
        cmd['in_sentence'] = bool(checked == Qt.Checked)
        self.log(f"InSentence for '{cmd['phrase']}' set to {cmd['in_sentence']}")
        self._save_commands()


    def _match_execution_criteria(self, phrase_F, cmd_phrase, in_sentence):
        self.log("got sentence with: " + phrase_F + cmd_phrase)
        if(not in_sentence):
            if "/" in cmd_phrase:
                cmd_single = cmd_phrase.split("/")
                for cmd_single_word in cmd_single:
                    self.log("Check1.5: " + cmd_single_word + " == " + phrase_F)
                    if cmd_single_word == phrase_F:
                        self.log("Matches sentence")
                        return True
            else:
                self.log("Check1: " + phrase_F + " == " + cmd_phrase)
                if phrase_F == cmd_phrase:
                    self.log("Matches sentence")
                    return True
        else:
            match_count = 0
            phrase_words = phrase_F.split(" ")
            cmd_words = cmd_phrase.split(" ")
            for word in phrase_words:
                for cmds in cmd_words:
                    if "/" in cmds:
                        cmd_single = cmds.split("/")
                        for cmd_single_word in cmd_single:
                            self.log("Check2: " + cmd_single_word + " == " + word)
                            if cmd_single_word == word:
                                match_count += 1
                                break
                    else:
                        self.log("Check3: " + cmds + " == " + word)
                        if cmds == word:
                            match_count += 1
            if match_count >= len(cmd_words):
                self.log("Matches sentence")
                return True
            else:
                self.log("Doesn't match sentence")
                return False

    def on_phrase_detected(self,phrase):
        for cmd in self.command_data:
            
            if cmd['enabled'] and (cmd['scope']=='global' or cmd['scope']==self.current_avatar_id):
                if self._match_execution_criteria(phrase, cmd['phrase'], cmd['in_sentence']):
                    for act in cmd['actions']:
                        if act['action_type'] != "Chatbox":
                            if (act['path'] == ""): continue
                            path = act['path']
                            if act.get('toggle'):
                                # invert last‑known bool (default False)
                                cur   = bool(self.param_values.get(path, False))
                                new_v = not cur
                            else:
                                if (act['value'] == ""): continue
                                new_v = act['value']

                            delay_s = act.get('delay', 0) or 0
                            self.scheduleOSC.emit(path, new_v, delay_s)
                        else:
                            path = act['path']
                            delay_s = act.get('delay', 0) or 0
                            self.scheduleOSC.emit("/chatbox/input", [path, True, False], delay_s)
                        

    @pyqtSlot(str, object, float)
    def _on_schedule_osc(self, path, new_v, delay_s):
        delay_ms = int(delay_s * 1000)

        if delay_ms > 0:
            QTimer.singleShot(delay_ms, lambda p=path, v=new_v: self.osc.send(p, v))
            self.log(f"Scheduled {path} → {new_v} in {delay_s}s")
        else:
            self.osc.send(path, new_v)
            self.log(f"Sent {path} → {new_v}")

    def _append_log(self, msg: str):
        t = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_widget.append(f'[{t}] {msg}')

    def log(self, msg: str):
        # this can be called from any thread
        self.logSignal.emit(msg)

class AddCommandDialog(QDialog):
    def __init__(self,parent=None,phrase="",actions=None,available_params=None,current_avatar=None,initial_scope='global'):
        super().__init__(parent)
        self.setWindowTitle("Command Editor")
        self.resize(900,700)
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
        self.actions_table = QTableWidget(0,5)
        self.actions_table.setColumnHidden(4, True)
        self.actions_table.setHorizontalHeaderLabels(["OSC Path","Value","Toggle?","Delay","action_type"])
        self.actions_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        layout.addWidget(self.actions_table)

        #chatbox events
        self.chatbox_table = QTableWidget(0,3)
        self.chatbox_table.setColumnHidden(2, True)
        self.chatbox_table.setHorizontalHeaderLabels(["Chatbox-text","Delay","action_type"])
        self.chatbox_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        layout.addWidget(self.chatbox_table)


        if actions:
            for act in actions:
                path   = act.get('path','')
                delay  = act.get('delay', 0)
                action_type = act.get('action_type', "OSC")
                # if this action was toggle‐only, there may be no 'value'

                if action_type == "Chatbox":
                    self.add_action_row(path=path, delay=str(delay), action_type=action_type)
                else:
                    valstr = str(act.get('value','0')) 
                    toggl  = act.get('toggle', False)
                    self.add_action_row(path=path, value=valstr, toggle=toggl, delay=str(delay), action_type=action_type)


        btns=QHBoxLayout()
        add_btn = QPushButton("Add Action") 
        add_btn.clicked.connect(lambda: self.add_action_row())
        btns.addWidget(add_btn)

        add_ctbx_btn = QPushButton("Add Chatbox event") 
        add_ctbx_btn.clicked.connect(lambda: self.add_action_row(action_type="Chatbox"))
        btns.addWidget(add_ctbx_btn); layout.addLayout(btns)

        ok_cancel=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_cancel.accepted.connect(self.accept); ok_cancel.rejected.connect(self.reject)
        layout.addWidget(ok_cancel)


    def add_action_row(self, path="", value="0", toggle=False, delay="0", action_type="OSC", *_args):
        
        if(action_type != "Chatbox"):
            row = self.actions_table.rowCount()
            self.actions_table.insertRow(row)

            # — OSC path combo +
            combo = QComboBox(); combo.setEditable(True)
            combo.addItems([p['address'] for p in self.available_params])
            combo.setCurrentText(path)
            # substring matcher
            comp = QCompleter([p['address'] for p in self.available_params], combo)
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            combo.setCompleter(comp)
            self.actions_table.setCellWidget(row, 0, combo)

            # — Value field

            val_edit = QLineEdit(value)
            self.actions_table.setCellWidget(row, 1, val_edit)

            action_edit = QLineEdit(action_type)
            self.actions_table.setCellWidget(row, 4, action_edit)

            # — Toggle? checkbox (only active for Bool params)
            cb = QCheckBox()
            # find this path’s type
            ptype = next((p['type'] for p in self.available_params if p['address']==path), None)
            # Option A: wrap in bool()
            #should_enable = toggle
            cb.setEnabled(True)
            val_edit.setEnabled(not toggle)
            cb.setChecked(toggle)

            # disable the value field whenever toggle is on
            cb.stateChanged.connect(lambda s, ve=val_edit: ve.setEnabled(s!=Qt.Checked))

            # Delay editor
            delay_item = QLineEdit(str(delay))
            delay_item.setValidator(QDoubleValidator(0.0, 999.0, 2))  # optional: only floats
            self.actions_table.setCellWidget(row, 3, delay_item)

            self.actions_table.setCellWidget(row, 2, cb)
        else:
            row = self.chatbox_table.rowCount()
            self.chatbox_table.insertRow(row)

            # — OSC path combo +
            combo = QComboBox(); combo.setEditable(True)
            combo.setCurrentText(path)
            self.chatbox_table.setCellWidget(row, 0, combo)

            # Delay editor
            delay_item = QLineEdit(str(delay))
            delay_item.setValidator(QDoubleValidator(0.0, 999.0, 2))  # optional: only floats
            self.chatbox_table.setCellWidget(row, 1, delay_item)

            action_edit = QLineEdit(action_type)
            self.chatbox_table.setCellWidget(row, 2, action_edit)


    def get_result(self):
        phrase = self.phrase_edit.text().strip().lower()
        scope = 'global' if self.global_rb.isChecked() else self.current_avatar
        
        actions = []
        for r in range(self.actions_table.rowCount()):
            path = self.actions_table.cellWidget(r,0).currentText().strip()
            toggle = self.actions_table.cellWidget(r,2).isChecked()
            delay_widget = self.actions_table.cellWidget(r, 3)
            action_type = self.actions_table.cellWidget(r, 4).text()

            try:
                delay = float(delay_widget.text())
            except ValueError:
                delay = 0.0

            if toggle: #todo check for actiontype
                actions.append({'path': path, 'toggle': True, 'delay':delay, 'action_type': action_type})
            else:
                vs = self.actions_table.cellWidget(r,1).text().strip().lower()
                
                if vs in ("true","false"):
                    v = (vs=="true")
                else:
                    try:    v = int(vs)
                    except: 
                        try: v = float(vs)
                        except: v = 0
                
                actions.append({'path': path, 'value': v, 'toggle': False, 'delay': delay, 'action_type': action_type})
        for r in range(self.chatbox_table.rowCount()):
            path = self.chatbox_table.cellWidget(r,0).currentText().strip()
            delay_widget = self.chatbox_table.cellWidget(r, 1)
            action_type = self.chatbox_table.cellWidget(r, 2).text()

            try:
                delay = float(delay_widget.text())
            except ValueError:
                delay = 0.0

            actions.append({'path': path, 'delay': delay, 'action_type': action_type})

        return phrase, actions, scope


class CommandListItemWidget(QWidget):
    def __init__(self, cmd, main_win, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.main = main_win

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)

        # enabled checkbox
        self.en_cb = QCheckBox()
        self.en_cb.setChecked(cmd['enabled'])
        self.en_cb.stateChanged.connect(self._toggle_enabled)
        lay.addWidget(self.en_cb)

        # phrase label
        lbl = QLabel(cmd['phrase'])
        lay.addWidget(lbl, stretch=1)

        # in‑sentence checkbox
        self.ins_cb = QCheckBox("InSentence")
        self.ins_cb.setChecked(cmd['in_sentence'])
        self.ins_cb.stateChanged.connect(self._toggle_in_sentence)
        lay.addWidget(self.ins_cb)

    def _toggle_enabled(self, state):
        self.cmd['enabled'] = (state == Qt.Checked)
        self.main.log(f"Command '{self.cmd['phrase']}' {'enabled' if self.cmd['enabled'] else 'disabled'}")
        self.main._save_commands()

    def _toggle_in_sentence(self, state):
        self.main._set_in_sentence(self.cmd, state)
