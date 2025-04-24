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

This tool allows you to define a voice command, which you can link to multiple OSC actions. The program allows setting bool/int/floats. For bool's you can enable a toggle mode, which flips the bool every time you speak the associated command. Right now the tool only triggers if the command is recognized as a standalone word, but there will be an option in the future to always react to commands, even when recognized in a sentence.

All voice recognition runs locally. With a voice recognition model by VOSK, it uses around 300 MB of RAM at Runtime. The Tool doesn't connect to any service except for the locally running VRChat OSC connection.

### 🏗️ Built With

- **Language/Framework:** Python 3.12
- **Key Libraries / Tools:**
  - [VOSK Voice Recognition](https://alphacephei.com/vosk/) – Used to detect what you are saying
 
### 💡 Planned features
- [x] In sentence recognition -> v0.2
- [x] Delayed actions -> v0.2
- [ ] Chat box Integration
- [ ] Modular chat box, example: "chat(trigger-word) hello there (to be written to the chat box)"
- [ ] JSON per avatar config in/export
- [ ] En/disable voice recognition via OSC-Parameter
- [ ] Optionally listen to game sound, to allow others to control your avatar
- [ ] Emotion detection, to be able to map emotions to facial expressions
- [ ] Action recording

## ⚙️ Installation

Download the latest installer from [releases](https://github.com/DeMuenu/VoiceToOSC/releases) and install it to a non-admin folder. (The standard path works)

## 🚀 Usage
You need to turn on OSC in the Action Menu under OSC > Enabled.

### Settings
The settings at the top of the window do the following:
**Outgoing Host**, is the IP where VRChat hosts the OSC endpoints.
**Outgoing Port**, is the Port where VRChat receives data.
**Incoming Port**, is the Port where VRChat sends data.

You don't need to change these settings if you don't have any other OSC-programs running. Only change these settings if you need to use an OSC-Router or similar. I was able to use VRCFaceTracking without any routing programs, so try if the programs can run alongside each other before setting up a router.

**Vosk model**, allows you to change the speech detection model, if you want to use one in your preferred language.
Get models from [VOSK models](https://alphacephei.com/vosk/models) (the sub-50M ones), unzip them and place them into the installation_path/models folder. After restarting, you should be able to select them from the drop-down.

**Input Device**, allows you to select the used microphone.

### Commands
You can add/edit/delete commands with the buttons visible. A command is the word or multiple Words you want to say to trigger the assigned actions. Commands that are assigned to a specific avatar will not show up unless you wear that avatar.

When creating a command, you will need to fill out the following things:
**Voice Phrase** Will be the trigger word/sentence. Keep in mind that the voice recognition models are small and not too advanced, so try to use easy words.

**Global/Avatar-specific** will make the command execute either always, or only when wearing the avatar you are wearing at the time of creation/editing.

**Actions**
You can add multiple actions to a command.

The ***OSC Path*** is the path where your avatar stores the variable you want to edit. This is the parameter name you define in the Unity editor when creating toggles. Since you might be using a public avatar or don't know what your parameter is called, you can search for parameters by typing the most probable name into the input field, and it will suggest all available parameters that contain the input text. Parameters don't have to be named the same way they are named in the radial menu, so if you can't find a "hat" parameter, you might want to search for "cap" or something similar. 

***Value*** is the value the selected parameter will be set to when the command is triggered. For boolean's (normal toggles), 0 is off and 1 is on. Floats (the ones where you get a radial number selection) can be set between 0 and 1. So if you have it set to 0.5, it corresponds to 50% in the radial menu. 

***Toggle?*** Allows you to toggle a bool. So if the parameter you selected is a boolean, you can enable Toggle, and it will switch between 0 and 1 when the command is Triggered. This won't work for floats and ints. 


***Tipp*** If you want to switch between different toggles in the game, create multiple commands, one that disables all the items you want to disable and toggles the one you want to enable. And other ones that also disable every toggle except the toggle that should be enabled when that command is triggered, which should be set to toggle. This allows you to switch between these toggles, and if you want to completely disable all the Toggles, you just need to say the last command again.


If the program crashes on startup after you changed something, go into the program folder and delete commands.json and settings.json
The standard path is: %AppData%\Local\VoiceToOSC  !!! This deletes your commands/settings !!!


