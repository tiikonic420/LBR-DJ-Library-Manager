"""Interpreter-local focus eligibility for cached, overlapping content pages.

No widget options, bindings or engine state are rewritten. Secondary top-levels
use the original Tk focus rules. The policy has no worker or database access.
"""
class PageFocusPolicy:
    def __init__(self, root):
        self.root = root
        tk = root.tk
        tk.call('auto_load', '::tk::FocusOK')
        tk.eval(r'''
namespace eval ::lbrPageFocus {
    variable root {}
    variable pages {}
    variable active {}
    variable fallback {}
    proc eligible {w} {
        variable root; variable pages; variable active
        if {![winfo exists $w]} {return 1}
        if {[winfo toplevel $w] ne $root} {return 1}
        foreach page $pages {
            if {$w eq $page || [string first "${page}." $w] == 0} {
                return [expr {$page eq $active}]
            }
        }
        return 1
    }
    proc guard {w} {
        variable fallback
        if {![eligible $w] && [winfo exists $fallback]} {
            nativeFocus $fallback
        }
    }
}
if {[llength [info commands ::lbrPageFocus::nativeFocusOK]] == 0} {
    rename ::tk::FocusOK ::lbrPageFocus::nativeFocusOK
    proc ::tk::FocusOK {w} {
        if {![::lbrPageFocus::eligible $w]} {return 0}
        tailcall ::lbrPageFocus::nativeFocusOK $w
    }
    rename ::focus ::lbrPageFocus::nativeFocus
    proc ::focus {args} {
        set target {}
        if {[llength $args] == 1 && ![string match -* [lindex $args 0]]} {
            set target [lindex $args 0]
        } elseif {[llength $args] == 2 && [lindex $args 0] eq "-force"} {
            set target [lindex $args 1]
        }
        if {$target ne {} && ![::lbrPageFocus::eligible $target]} {return {}}
        tailcall ::lbrPageFocus::nativeFocus {*}$args
    }
    bind all <FocusIn> {+::lbrPageFocus::guard %W}
}
''')
        tk.call('set', '::lbrPageFocus::root', str(root))

    def activate(self, pages, active, fallback):
        tk = self.root.tk
        tk.call('set', '::lbrPageFocus::pages', tuple(str(p) for p in pages))
        tk.call('set', '::lbrPageFocus::active', str(active))
        tk.call('set', '::lbrPageFocus::fallback', str(fallback))
        focused = self.root.focus_get()
        if focused is not None and not tk.getboolean(
                tk.call('::lbrPageFocus::eligible', str(focused))):
            fallback.focus_set()
