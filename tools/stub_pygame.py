"""stub_pygame.py - 提供一个完整的 stub pygame 让 src/* 可被 import + 实例化"""
import sys, types

class _S:
    type = 0
    key = 0
    def __init__(self, *a, **kw):
        # 常见用法: Event(type, {key: K_z}) -> type & key
        if len(a) >= 1:
            self.type = a[0]
        if len(a) >= 2 and isinstance(a[1], dict):
            for k, v in a[1].items():
                setattr(self, k, v)
        for k, v in kw.items():
            setattr(self, k, v)
    def convert_alpha(self): return self
    def fill(self, *a, **kw): pass
    def blit(self, *a, **kw): pass
    def blits(self, *a, **kw): return []
    def set_at(self, *a, **kw): pass
    def get_width(self): return 100
    def get_height(self): return 100
    def set_alpha(self, *a, **kw): pass
    def render(self, *a, **kw): return _S()
    def tick(self, *a, **kw): return 16
    def get_ticks(self): return 0
    def set_mode(self, *a, **kw): return _S()
    def set_caption(self, *a, **kw): pass
    def flip(self): pass
    def init(self): pass
    def quit(self): pass
    def Sound(self, *a, **kw): pass
    def play(self): pass
    def get(self, k, default=None): return default

# 完整 key map
KEYS = {
    "K_UP":273,"K_DOWN":274,"K_LEFT":276,"K_RIGHT":275,
    "K_w":119,"K_a":97,"K_s":115,"K_d":100,
    "K_LSHIFT":1075,"K_RSHIFT":1076,
    "K_z":122,"K_x":120,
    "K_F1":282,"K_F2":283,"K_F3":284,"K_F4":285,
    "K_p":112,"K_ESCAPE":27,
    "K_RETURN":13,"K_SPACE":32,
}

def install_pygame_stub():
    pg = types.ModuleType("pygame")
    pg.Surface = _S
    pg.Rect = _S
    pg.font = types.SimpleNamespace(SysFont=lambda *a,**kw: _S(), init=lambda:None, quit=lambda:None)
    pg.event = types.SimpleNamespace(get=lambda:[], Event=lambda *a, **kw: _S(*a, **kw))
    pg.time = types.SimpleNamespace(Clock=_S, get_ticks=lambda:0)
    pg.display = types.SimpleNamespace(set_mode=lambda *a,**kw: _S(), set_caption=lambda *a,**kw:None, flip=lambda:None)
    pg.draw = types.SimpleNamespace(circle=lambda *a,**kw:None, polygon=lambda *a,**kw:None,
                                     rect=lambda *a,**kw:None, line=lambda *a,**kw:None)
    pg.mixer = types.SimpleNamespace(init=lambda:None, quit=lambda:None, Sound=_S)
    for n, v in KEYS.items():
        setattr(pg, n, v)
    pg.QUIT = 256
    pg.KEYDOWN = 768
    pg.KEYUP = 769
    pg.init = lambda: None
    pg.quit = lambda: None
    sys.modules["pygame"] = pg
    return pg