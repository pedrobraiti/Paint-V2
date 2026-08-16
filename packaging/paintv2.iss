; Instalador do Paint-V2 (Inno Setup 6).
;
; Instala por usuário em %LOCALAPPDATA%\Programs por padrão, o que dispensa
; elevação — mas o instalador oferece a instalação para todos os usuários a quem
; tiver permissão. O atalho no Menu Iniciar é o que faz o app aparecer ao
; pesquisar "Paint" no Windows.
;
; Compilar com:  iscc packaging\paintv2.iss

#define AppName "Paint-V2"
#define AppVersion "1.0.0"
#define AppPublisher "Paint-V2"
#define AppExeName "Paint-V2.exe"
#define AppId "{8B4F2E1C-7D3A-4C6B-9E5F-1A2B3C4D5E6F}"

[Setup]
AppId={{#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename=Paint-V2-Setup-{#AppVersion}
SetupIconFile=..\src\paintv2\resources\paintv2.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais"
Name: "associate"; Description: "Adicionar o {#AppName} ao menu ""Abrir com"" das imagens"; GroupDescription: "Integração com o Windows"

[Files]
Source: "..\dist\{#AppName}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Excludes: "{#AppExeName}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Comment: "Editor de imagens com pincéis de saturação e blend"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; ProgId próprio: aparece em "Abrir com" sem roubar o programa padrão do usuário.
Root: HKA; Subkey: "Software\Classes\PaintV2.Image"; ValueType: string; ValueName: ""; ValueData: "Imagem do {#AppName}"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\PaintV2.Image\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\PaintV2.Image\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.png\OpenWithProgids"; ValueType: string; ValueName: "PaintV2.Image"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.jpg\OpenWithProgids"; ValueType: string; ValueName: "PaintV2.Image"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.jpeg\OpenWithProgids"; ValueType: string; ValueName: "PaintV2.Image"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.bmp\OpenWithProgids"; ValueType: string; ValueName: "PaintV2.Image"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.webp\OpenWithProgids"; ValueType: string; ValueName: "PaintV2.Image"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; ValueType: string; ValueName: ".png"; ValueData: ""; Flags: uninsdeletekey; Tasks: associate

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o {#AppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
