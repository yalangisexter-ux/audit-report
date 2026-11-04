#define MyAppName "Raw Strength Calisthenics - Employee Audit Manager"
#define MyAppVersion "1.3.74"
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
UsePreviousAppDir=yes
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

[Files]
Source: "dist\RawStrengthEmployeeAuditManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: dontcopy
Source: "update_recovery.ps1"; DestDir: "{tmp}"; Flags: dontcopy
Source: "resolve_customer_data_dir.ps1"; DestDir: "{tmp}"; Flags: dontcopy

[Icons]
Name: "{group}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Raw Strength Employee Audit Manager"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Raw Strength Employee Audit Manager"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
var
	InstallDirectory: String;
	DataDirectory: String;
	PendingBackupDirectory: String;
	StableBackupDirectory: String;
	RecoveryScriptPath: String;
	TransactionBackupReady: Boolean;
	TransactionInstallSucceeded: Boolean;

function RecoveryPowerShellPath: String;
begin
	Result := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
end;

function RunRecoveryScript(const Mode: String; const ExtraArguments: String; var ResultCode: Integer): Boolean;
var
	Arguments: String;
begin
	Arguments := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + AddQuotes(RecoveryScriptPath) +
		' -Mode ' + Mode + ' -InstallDir ' + AddQuotes(InstallDirectory) +
		' -BackupDir ' + AddQuotes(PendingBackupDirectory) +
		' -StableBackupDir ' + AddQuotes(StableBackupDirectory) + ExtraArguments;
	Result := Exec(RecoveryPowerShellPath, Arguments, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function KillRunningAppProcess: Boolean;
var
	ResultCode: Integer;
begin
	Result := True;
	Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM RawStrengthEmployeeAuditManager.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
	Sleep(750);
end;

function GetCustomerDataDirectory: String;
var
	ScriptPath: String;
	OutputPath: String;
	ResultCode: Integer;
begin
	Result := Trim(ExpandConstant('{param:DATA_DIR|}'));
	if Result <> '' then
		Exit;

	// Very old clients do not pass DATA_DIR. Resolve the interactive user's
	// actual profile instead of using the elevated administrator's LOCALAPPDATA.
	ScriptPath := ExpandConstant('{tmp}\resolve_customer_data_dir.ps1');
	OutputPath := ExpandConstant('{tmp}\rsc_customer_data_dir.txt');
	DeleteFile(OutputPath);
	ExtractTemporaryFile('resolve_customer_data_dir.ps1');
	if Exec(RecoveryPowerShellPath, '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' + AddQuotes(ScriptPath) + ' -OutputFile ' + AddQuotes(OutputPath), '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) and LoadStringFromFile(OutputPath, Result) then
	begin
		Result := Trim(Result);
		if Result <> '' then
			Exit;
	end;

	// A fresh install has no previous customer data to locate. For an existing
	// installation, fail closed rather than accidentally selecting the admin profile.
	if FileExists(InstallDirectory + '\RawStrengthEmployeeAuditManager.exe') then
		Result := ''
	else
		Result := ExpandConstant('{localappdata}\EmployeeAuditManager');
end;

function InitializeSetup: Boolean;
begin
	InstallDirectory := ExpandConstant('{autopf}\Raw Strength Employee Audit Manager');
	DataDirectory := Trim(ExpandConstant('{param:DATA_DIR|}'));
	PendingBackupDirectory := '';
	StableBackupDirectory := '';
	TransactionBackupReady := False;
	TransactionInstallSucceeded := False;
	Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
	ResultCode: Integer;
begin
	Result := '';
	NeedsRestart := False;
	InstallDirectory := ExpandConstant('{app}');
	DataDirectory := GetCustomerDataDirectory;
	if DataDirectory = '' then
	begin
		Result := 'Could not identify the original customer Windows profile. The update was stopped to protect the existing database. Please retry the update from the installed application.';
		Exit;
	end;
	PendingBackupDirectory := AddBackslash(DataDirectory) + 'pending-update-backup';
	StableBackupDirectory := AddBackslash(DataDirectory) + 'previous-version';
	RecoveryScriptPath := ExpandConstant('{tmp}\update_recovery.ps1');
	if DirExists(InstallDirectory) and FileExists(InstallDirectory + '\RawStrengthEmployeeAuditManager.exe') then
	begin
		KillRunningAppProcess;
		ExtractTemporaryFile('update_recovery.ps1');
		if not RunRecoveryScript('backup', '', ResultCode) or (ResultCode <> 0) then
		begin
			Sleep(1000);
			if not RunRecoveryScript('backup', '', ResultCode) or (ResultCode <> 0) then
			begin
				Result := 'Could not protect the existing installation before updating. The current app was left in place.';
				Exit;
			end;
		end;
		TransactionBackupReady := True;
	end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
	ResultCode: Integer;
	ExtraArguments: String;
begin
	if CurStep = ssPostInstall then
	begin
		RecoveryScriptPath := ExpandConstant('{tmp}\update_recovery.ps1');
		ExtractTemporaryFile('update_recovery.ps1');
		ExtraArguments := ' -ExpectedVersion ' + AddQuotes('{#MyAppVersion}') +
			' -DataDir ' + AddQuotes(DataDirectory);
		if not RunRecoveryScript('launch-check', ExtraArguments, ResultCode) or (ResultCode <> 0) then
		begin
			if TransactionBackupReady then
			begin
				if RunRecoveryScript('restore', '', ResultCode) and (ResultCode = 0) then
					TransactionBackupReady := False
				else
					RaiseException('The updated app did not start correctly, and automatic rollback could not finish. The previous app copy is retained at: ' + PendingBackupDirectory);
			end
			else
			begin
				RunRecoveryScript('remove-new', '', ResultCode);
				RaiseException('The updated app did not start correctly. The incomplete installation was removed.');
			end;
			RaiseException('The updated app did not pass its startup check. The existing version has been restored.');
		end;
	end
	else if CurStep = ssDone then
	begin
		// The original, unelevated updater process relaunches the app after Setup exits.
		// Interactive installs use the [Run] entry with runasoriginaluser.
		TransactionInstallSucceeded := True;
	end;
end;

procedure DeinitializeSetup;
var
	ResultCode: Integer;
begin
	if TransactionBackupReady then
	begin
		if TransactionInstallSucceeded then
		begin
			if not RunRecoveryScript('promote', '', ResultCode) or (ResultCode <> 0) then
				Log('Previous-version backup remains at ' + PendingBackupDirectory + ' because it could not be promoted.');
		end
		else if not RunRecoveryScript('restore', '', ResultCode) or (ResultCode <> 0) then
		begin
			MsgBox('Update failed and automatic rollback could not finish. The previous app copy is retained at:' + #13#10 + PendingBackupDirectory,
				mbError, MB_OK);
		end;
	end;
end;
