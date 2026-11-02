#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR arguments,int show){
    HANDLE mutex=CreateMutexW(NULL,FALSE,L"Local\\LBRSoftware.DJLibraryManager");
    if(!mutex)return 4;
    if(GetLastError()==ERROR_ALREADY_EXISTS){
        MessageBoxW(NULL,L"LBR DJ Library Manager est déjà ouvert. Retrouve sa fenêtre dans la barre des tâches.",L"LBR DJ Library Manager",MB_OK|MB_ICONINFORMATION);
        CloseHandle(mutex);return 0;
    }
    wchar_t root[32768],python[32768],script[32768],command[65536];
    DWORD n=GetModuleFileNameW(NULL,root,32768);
    if(!n || n>=32768)return 1;
    wchar_t *last=wcsrchr(root,L'\\');if(!last)return 1;*last=0;
    if(wcslen(root)>32000)return 1;
    swprintf(python,32768,L"%ls\\_internal\\python\\pythonw.exe",root);
    swprintf(script,32768,L"%ls\\_internal\\app\\start.pyw",root);
    if(GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES){
        MessageBoxW(NULL,L"Extrais le ZIP complet avant de lancer le programme. Le dossier _internal doit rester à côté du fichier .exe.",L"LBR DJ Library Manager",MB_OK|MB_ICONERROR);return 2;
    }
    swprintf(command,65536,L"\"%ls\" -I \"%ls\"",python,script);
    STARTUPINFOW startup={0};PROCESS_INFORMATION process={0};startup.cb=sizeof(startup);
    if(!CreateProcessW(python,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&startup,&process)){
        wchar_t message[512];swprintf(message,512,L"Le programme n'a pas pu démarrer (erreur Windows %lu). Vérifie que le ZIP a été entièrement extrait.",GetLastError());
        MessageBoxW(NULL,message,L"LBR DJ Library Manager",MB_OK|MB_ICONERROR);return 3;
    }
    CloseHandle(process.hThread);WaitForSingleObject(process.hProcess,INFINITE);
    DWORD result=0;GetExitCodeProcess(process.hProcess,&result);CloseHandle(process.hProcess);
    if(result && result!=10)MessageBoxW(NULL,L"Le programme s'est arrêté de manière inattendue. Consulte le journal dans %LOCALAPPDATA%\\LBR-DJ-Library-Manager\\logs.",L"LBR DJ Library Manager",MB_OK|MB_ICONERROR);
    return (int)result;
}
