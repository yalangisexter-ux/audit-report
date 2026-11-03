; Inno Setup script for Raw Strength Calisthenics Employee Audit Manager
#define MyAppVersion "1.3.69"
#define MyAppName "Raw Strength Calisthenics - Employee Audit Manager"
#define MyAppPublisher "Raw Strength Calisthenics"
#define MyAppExeName "RawStrengthEmployeeAuditManager.exe"
#define MyAppURL "https://github.com/yalangisexter-ux/audit-report"

[Setup]
AppId={{8F3C2A1B-9D4E-4F6A-B7C8-1E2D3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\RawStrengthEmployeeAuditManager
DefaultGroupName=Raw Strength Calisthenics
AllowNoIcons=yes
OutputDir=installer-output
OutputBaseFilename=RawStrengthEmployeeAuditManager-Setup
SetupIconFile=assets\raw_strength_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\RawStrengthEmployeeAuditManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
