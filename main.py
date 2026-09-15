from app.capture import dpi_aware

if __name__ == '__main__':
    dpi_aware()
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--diagnose',metavar='REPORT_JSON')
    parser.add_argument('--reference',metavar='IMAGE')
    args=parser.parse_args()
    if args.diagnose:
        import json
        from pathlib import Path
        import tkinter as tk
        from app.gui import RESOURCES
        from app.whitelist import load
        from app.recognition import recognize,match_items
        from app.capture import reference,detect
        from app.input_control import Safety
        root=tk.Tk();root.withdraw();root.update();root.destroy()
        safety=Safety()
        result={'tk':True,'whitelist_rows':len(load(RESOURCES/'app/default_whitelist.json')),'hotkey_registered':safety.hotkey_ok,'candidate_windows':len(detect()),'background_input':'unverified','sent_keys':0}
        safety.close()
        if args.reference:
            image,note=reference(args.reference)
            words=recognize(image,RESOURCES/'scripts/ocr.ps1')
            items=match_items(words,load(RESOURCES/'app/default_whitelist.json'),image.size)
            result.update(ocr_words=len(words),items=[x.__dict__ for x in items],reference_note=note)
        Path(args.diagnose).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        from app.gui import run
        run()
