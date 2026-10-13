; Inno Setup Script for FortiGate PM Report Generator
; Supports both Offline Installer (with bundled Qwen GGUF model) and Light Installer

#define MyAppName "FortiGate PM Report Generator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CTC Global"
#define MyAppExeName "start.bat"

[Setup]
AppId={{9C56A41B-B65B-4C92-A238-C18E5E72DC12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CTC\PMReportGenerator
DefaultGroupName={#MyAppName}
OutputDir=..\dist
#ifdef LightInstaller
OutputBaseFilename=PMReportGenerator-Light-Setup
#else
OutputBaseFilename=PMReportGenerator-Offline-Setup
#endif
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Root scripts and licenses
Source: "..\start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stop.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES.txt"; DestDir: "{app}"; Flags: ignoreversion

; Backend application source
Source: "..\backend\app\*"; DestDir: "{app}\backend\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\backend\run.py"; DestDir: "{app}\backend"; Flags: ignoreversion
Source: "..\backend\requirements.txt"; DestDir: "{app}\backend"; Flags: ignoreversion

; Pre-compiled Frontend distribution
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: ignoreversion recursesubdirs createallsubdirs

; DOCX Report Templates
Source: "..\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs

; Local AI Runtime (llama.cpp win-cpu-x64 binaries and DLLs)
Source: "..\bin\llama\*"; DestDir: "{app}\bin\llama"; Flags: ignoreversion recursesubdirs createallsubdirs

; Local AI Model (Offline Installer only: bundles verified Qwen3-1.7B-Q4_K_M.gguf)
; For light installer builds, pass -DLightInstaller to ISCC to exclude this line
#ifndef LightInstaller
Source: "..\models\local-ai\Qwen3-1.7B-Q4_K_M.gguf"; DestDir: "{localappdata}\CTC\PMReportGenerator\models"; Flags: ignoreversion
#endif

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall skipifsilent
