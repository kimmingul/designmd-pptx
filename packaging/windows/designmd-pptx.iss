; Inno Setup script — optional GUI one-file Setup.exe wrapper for #35.
; Build on Windows with Inno Setup 6+:
;   ISCC.exe packaging\windows\designmd-pptx.iss
; Output: packaging\windows\dist\DesignmdPptx-Setup.exe
;
; The Setup.exe extracts Install-DesignmdPptx.ps1 and runs it elevated-optional
; (per-user; no admin required by default). Uninstall invokes the same script
; with -Uninstall.

#define MyAppName "designmd-pptx"
#define MyAppVersion "2.1.2"
#define MyAppPublisher "designmd-pptx contributors"
#define MyAppURL "https://github.com/kimmingul/designmd-pptx"

[Setup]
AppId={{A7F3C2E1-9B4D-4F6A-8E21-DESIGNMDPPTX35}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={localappdata}\designmd-pptx
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=DesignmdPptx-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
InfoBeforeFile=INSTALL-INFO.txt
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; One-file installer payload
Source: "Install-DesignmdPptx.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "INSTALL-INFO.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{userprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Install-DesignmdPptx.ps1"" -Uninstall"; WorkingDir: "{app}"
Name: "{userprograms}\{#MyAppName}\designmd-pptx doctor"; Filename: "{app}\bin\designmd-pptx.cmd"; Parameters: "doctor"; WorkingDir: "{app}"; Flags: createonlyiffileexists

[Run]
; After files are laid down, run the real installer (venv + officecli pin + PATH)
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Install-DesignmdPptx.ps1"" -InstallRoot ""{app}"""; \
  StatusMsg: "Installing Python venv, designmd-pptx, and pinned OfficeCLI…"; \
  Flags: waituntilterminated

[UninstallRun]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\Install-DesignmdPptx.ps1"" -Uninstall -InstallRoot ""{app}"""; \
  RunOnceId: "DesignmdPptxUninstall"; Flags: waituntilterminated

[Code]
// Ensure PowerShell exists (Windows 7+ ships it; fail clearly otherwise)
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if not Exec('powershell.exe', '-NoProfile -Command "exit 0"', '', SW_HIDE,
              ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('PowerShell is required to install designmd-pptx.', mbError, MB_OK);
    Result := False;
  end;
end;
