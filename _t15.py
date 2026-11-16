import traceback, conn_widget as cw
def p(*a): print(*a, flush=True)
cfg = cw.load_cfg()
cfg.update({"x": 1400, "y": 100, "first_run_done": True})
w = cw.ConnWidget(cfg)
def go():
    try:
        w.open_settings(); p("settings ok")
        w.check_update()
        w.root.after(4000, lambda: (p("label:", w.update_lbl.cget("text")), w.quit_app()))
    except Exception:
        traceback.print_exc(); w.quit_app()
w.root.after(1500, go)
w.run()
p("done")
