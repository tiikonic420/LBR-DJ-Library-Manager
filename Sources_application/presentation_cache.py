"""Avoid repeating an unchanged TagStudio presentation-only Tcl write."""
def cache_pending_foreground(tree, hub):
    if getattr(tree, '_lbr_pending_foreground_cached', False):
        return
    original = tree.tag_configure
    cached = {}

    def configure(tagname, option=None, **kw):
        eligible = tagname == 'pending' and option is None and set(kw) == {'foreground'} and kw['foreground'] is not None
        if eligible and cached.get('foreground') == kw['foreground']:
            return {}

        def apply():
            # A worker miss is checked again on the UI thread. The Tcl write and
            # cache update stay in the same UI callback, including theme changes.
            if eligible and cached.get('foreground') == kw['foreground']:
                return {}
            result = original(tagname, option, **kw)
            if eligible:
                cached['foreground'] = kw['foreground']
            elif tagname == 'pending' and kw:
                cached.clear()
            return result
        return hub.ui(apply)

    tree.tag_configure = configure
    tree._lbr_pending_foreground_cached = True
