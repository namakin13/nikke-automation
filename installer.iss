; installer.iss
; Inno Setup 6 スクリプト
; build.bat から自動実行されます。単独で実行する場合:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#define AppName    "NIKKE Automation"
#define AppVersion "1.0.0"
#define AppExeName "NikkeAutomation.exe"
#define SourceDir  "dist\NikkeAutomation"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=NikkeAutomation_Setup
OutputDir=dist
Compression=lzma2/ultra64
SolidCompression=yes
; 管理者権限不要でインストール可能（ユーザーの AppData へ）
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
WizardStyle=modern
WizardSmallImageFile=

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; \
    GroupDescription: "追加タスク:"; Flags: unchecked

[Files]
; PyInstaller の onedir 出力をそのまま収録
Source: "{#SourceDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\アンインストール";    Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "{#AppName} を起動する"; \
    Flags: nowait postinstall skipifsilent
