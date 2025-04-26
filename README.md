<a id="readme-top"></a>

<br />

<div align="center">
  <h1 align="center">Voice to VRChat-OSC</h1>
  <p align="center">
    An Application for VRChat, that allows you to simply map voice commands to avatar toggles.
    <br />
    <a href="https://github.com/DeMuenu/VoiceToOSC/issues/new?labels=bug&template=bug-report.md">Report Bug</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/DeMuenu/VoiceToOSC/issues/new?labels=enhancement&template=feature-request.md">Request Feature</a>
  </p>
</div>

---

## 📖 About

This tool allows you to define a voice command, which you can link to multiple OSC actions. The program allows setting bool/int/floats. For bool's you can enable a toggle mode, which flips the bool every time you speak the associated command. There is also a voice to chatbox mode, with live preview and triggerwords.

All voice recognition runs locally. With a voice recognition model by VOSK, it uses around 300 MB of RAM at Runtime. The Tool doesn't connect to any service except for the locally running VRChat OSC connection and a update check when starting the programm.

### 🏗️ Built With

- **Language/Framework:** Python 3.13
- **Key Libraries / Tools:**
  - [VOSK Voice Recognition](https://alphacephei.com/vosk/) – Used to detect what you are saying
 
### 💡 Planned features
- [x] In sentence recognition → v0.0.2
- [x] Delayed actions → v0.0.2
- [x] Chat box Integration → v0.0.3
- [x] Modular chat box, example: "chat(trigger-word) hello there (to be written to the chat box)" → v0.0.3
- [ ] JSON per avatar config in/export
- [ ] En/disable voice recognition via OSC-Parameter
- [ ] Optionally listen to game sound, to allow others to control your avatar
- [ ] Emotion detection, to be able to map emotions to facial expressions
- [ ] Action recording

## ⚙️ Installation

Download the latest installer from [releases](https://github.com/DeMuenu/VoiceToOSC/releases) and install it to a non-admin folder. (The standard path works)

To update the program, just install the new version into the same folder (I'd recommend to just always keep the standard path). It will override the .exe and internals, but keep your config, settings and models.

## 🚀 Usage
You need to turn on OSC in the Action Menu under OSC > Enabled.

To see how to configure Commands and TextToChatbox, see the [wiki](https://github.com/DeMuenu/VoiceToOSC/wiki).
