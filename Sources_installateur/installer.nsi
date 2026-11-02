Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!ifndef PAYLOAD_DIR
!define PAYLOAD_DIR "payload"
!endif
!ifndef RELEASE_TAG
!define RELEASE_TAG "5.0 RC"
!endif
Name "LBR DJ Library Manager ${RELEASE_TAG}"
OutFile "LBR_DJ_Library_Manager_${RELEASE_TAG}_Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\LBR Software\LBR DJ Library Manager ${RELEASE_TAG}"
InstallDirRegKey HKCU "Software\LBR Software\DJ Library Manager ${RELEASE_TAG}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!ifndef NUMERIC_VERSION
!define NUMERIC_VERSION "5.0.0.0"
!endif
VIProductVersion "${NUMERIC_VERSION}"
VIAddVersionKey /LANG=1036 "ProductName" "LBR DJ Library Manager"
VIAddVersionKey /LANG=1036 "CompanyName" "LBR Software"
VIAddVersionKey /LANG=1036 "FileDescription" "Installation LBR DJ Library Manager"
VIAddVersionKey /LANG=1036 "FileVersion" "${RELEASE_TAG}"
VIAddVersionKey /LANG=1036 "LegalCopyright" "LBR Software"
!define MUI_ICON "lbr.ico"
!define MUI_UNICON "lbr.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "Installe les quatre outils DJ, leur moteur commun et leurs dépendances.$\r$\n$\r$\nVersion gratuite • LBR Software$\r$\n$\r$\nVersion candidate ${RELEASE_TAG} : validation finale sous Windows requise."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\LBR_DJ_Library_Manager.exe"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "French"
Var AppMutex
!macro CheckClosed
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\LBRSoftware.DJLibraryManager") p .r0 ?e'
  Pop $1
  StrCpy $AppMutex $0
  ${If} $1 = 183
    System::Call 'kernel32::CloseHandle(p $AppMutex)'
    StrCpy $AppMutex 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "Ferme LBR DJ Library Manager avant de continuer. Attends la fin des tâches en cours."
    Abort
  ${EndIf}
!macroend
Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Cette version nécessite Windows 64 bits."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Cette version nécessite Windows 10 ou 11."
    Abort
  ${EndIf}
  SetRegView 64
  SetShellVarContext current
  !insertmacro CheckClosed
FunctionEnd
Function .onInstSuccess
  System::Call 'kernel32::CloseHandle(p $AppMutex)'
  StrCpy $AppMutex 0
FunctionEnd
Function .onGUIEnd
  ${If} $AppMutex != 0
    System::Call 'kernel32::CloseHandle(p $AppMutex)'
  ${EndIf}
FunctionEnd
Section "Programme et moteurs (obligatoire)" Main
  SectionIn RO
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD_DIR}\*"
  WriteUninstaller "$INSTDIR\Desinstaller.exe"
  WriteRegStr HKCU "Software\LBR Software\DJ Library Manager ${RELEASE_TAG}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "DisplayName" "LBR DJ Library Manager"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "DisplayVersion" "${RELEASE_TAG}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "Publisher" "LBR Software"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "UninstallString" '$\"$INSTDIR\Desinstaller.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "DisplayIcon" "$INSTDIR\LBR_DJ_Library_Manager.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}" "NoRepair" 1
  CreateDirectory "$SMPROGRAMS\LBR Software"
  CreateShortcut "$SMPROGRAMS\LBR Software\LBR DJ Library Manager ${RELEASE_TAG}.lnk" "$INSTDIR\LBR_DJ_Library_Manager.exe"
  CreateShortcut "$SMPROGRAMS\LBR Software\Guide LBR DJ ${RELEASE_TAG}.lnk" "$INSTDIR\Documentation\GUIDE_UTILISATEUR.md"
SectionEnd
Section /o "Raccourci sur le Bureau" Desktop
  CreateShortcut "$DESKTOP\LBR DJ Library Manager ${RELEASE_TAG}.lnk" "$INSTDIR\LBR_DJ_Library_Manager.exe"
SectionEnd
Function un.onInit
  SetRegView 64
  SetShellVarContext current
  !insertmacro CheckClosed
FunctionEnd
Function un.onGUIEnd
  ${If} $AppMutex != 0
    System::Call 'kernel32::CloseHandle(p $AppMutex)'
  ${EndIf}
FunctionEnd
Section "Uninstall"
  Delete "$DESKTOP\LBR DJ Library Manager ${RELEASE_TAG}.lnk"
  Delete "$SMPROGRAMS\LBR Software\LBR DJ Library Manager ${RELEASE_TAG}.lnk"
  Delete "$SMPROGRAMS\LBR Software\Guide LBR DJ ${RELEASE_TAG}.lnk"
  RMDir "$SMPROGRAMS\LBR Software"
  Delete "$INSTDIR\LBR_DJ_Library_Manager.exe"
  Delete "$INSTDIR\Desinstaller.exe"
  Delete "$INSTDIR\VERSIONS.json"
  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\Documentation"
  RMDir /r "$INSTDIR\Licences"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\LBRDJLibraryManager_${RELEASE_TAG}"
  DeleteRegKey HKCU "Software\LBR Software\DJ Library Manager ${RELEASE_TAG}"
  DetailPrint "Tes réglages, sauvegardes et bibliothèques musicales ont été conservés."
SectionEnd
