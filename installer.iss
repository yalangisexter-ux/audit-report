#define MyAppName "Raw Strength Calisthenics - Employee Audit Manager"
#define AppVersionEnv GetEnv("APP_VERSION")
#if AppVersionEnv == ""
	#define MyAppVersion "1.2.96"
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
Source: "dist\RawStrengthEmployeeAuditManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: dontcopy

[Icons]
Name: "{group}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Raw Strength Employee Audit Manager"; Flags: nowait

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
	ResultCode: Integer;
begin
	Result := '';
	// Do not delete the existing installation before the new install is ready.
	// Inno Setup updates managed files in place; user data is stored separately in Local AppData.
	ExtractTemporaryFile('vc_redist.x64.exe');
	if not Exec(ExpandConstant('{tmp}\vc_redist.x64.exe'), '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
	begin
		Result := 'Could not start the Microsoft Visual C++ Redistributable installer.';
		Exit;
	end;

	if (ResultCode <> 0) and (ResultCode <> 3010) and (ResultCode <> 1638) then
		Result := Format('The Microsoft Visual C++ Redistributable installer failed with exit code %d.', [ResultCode])
	else if ResultCode = 3010 then
		NeedsRestart := True;
end;
