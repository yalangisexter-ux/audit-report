#define MyAppName "Raw Strength Calisthenics - Employee Audit Manager"
#define AppVersionEnv GetEnv("APP_VERSION")
#if AppVersionEnv == ""
	#define MyAppVersion "1.0.0"
#else
	#define MyAppVersion AppVersionEnv
#endif
#define MyAppPublisher "Raw Strength Calisthenics"
#define MyAppExeName "RawStrengthEmployeeAuditManager.exe"

[Setup]
AppId={{4A2A33C8-8C51-4CF5-A6B0-8D5F9F9A42D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/yalangisexter-ux/audit-report
AppSupportURL=https://github.com/yalangisexter-ux/audit-report
AppUpdatesURL=https://github.com/yalangisexter-ux/audit-report
DefaultDirName={autopf}\Raw Strength Employee Audit Manager
DefaultGroupName={#MyAppName}
OutputDir=installer-output
OutputBaseFilename=RawStrengthEmployeeAuditManager-Setup
SetupIconFile=assets\raw_strength_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
Uninstallable=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
; The app database is stored in {localappdata}\EmployeeAuditManager, not here.
; Do not add any uninstall cleanup for user data/backups.

[Files]
Source: "dist\RawStrengthEmployeeAuditManager.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Raw Strength Employee Audit Manager"; Flags: nowait postinstall skipifsilent
