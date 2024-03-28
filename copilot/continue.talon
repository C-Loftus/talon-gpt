app: vscode
-

## Commands to interact with https://continue.dev/ extension

tin you new: user.vscode("continue.newSession")
tin you file select: user.vscode("continue.selectFilesAsContext")
tin you history: user.vscode("continue.viewHistory")
tin you (accept | yes): user.vscode("continue.acceptDiff")
tin you (reject | cancel): user.vscode("continue.rejectDiff")
tin you toggle fullscreen: user.vscode("continue.toggleFullScreen")
tin you next: user.vscode("editor.action.inlineSuggest.showNext")
tin you (previous | last): user.vscode("editor.action.inlineSuggest.showPrevious")
tin you jest: user.vscode("editor.action.inlineSuggest.trigger")
tin you debug terminal: user.vscode("continue.debugTerminal")
tin you add <user.cursorless_target>:
    user.cursorless_command("setSelection", cursorless_target)
    user.vscode("continue.focusContinueInput")
tin you quick edit <user.cursorless_target>:
    user.cursorless_command("setSelection", cursorless_target)
    user.vscode("continue.quickEdit")

bar tin you: user.vscode("continue.continueGUIView.focus")
