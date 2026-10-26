; Inno Setup script for Pandora's Box Remaster.
; Built with: iscc /DAppVersion=x.y.z packaging\windows\installer.iss
; Expects dist\PandorasBoxRemaster\ (PyInstaller onedir) to exist already.
; The original game files are not included: the game asks for them on first start.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Pandora's Box Remaster"
#define ExeName "PandorasBoxRemaster.exe"
#define RepoRoot AddBackslash(SourcePath) + "..\.."

[Setup]
AppId={{7DF3E4A6-2DA3-42F5-85B4-AE280AB9C6C4}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Mike Hellyer
DefaultDirName={autopf}\Pandoras Box Remaster
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#ExeName}
OutputDir={#RepoRoot}\dist
OutputBaseFilename=PandorasBoxRemaster-{#AppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile={#RepoRoot}\packaging\icons\icon.ico
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#RepoRoot}\dist\PandorasBoxRemaster\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; a fresh copy of the bundle each time, so files from an older version don't linger
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
