from app.capture import dpi_aware

if __name__ == '__main__':
    dpi_aware()
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--diagnose',metavar='REPORT_JSON')
    parser.add_argument('--reference',metavar='IMAGE')
    parser.add_argument('--mode',choices=['quest','material'],default='quest')
    parser.add_argument('--flow-check',action='store_true',help='Offline screen-state diagnostic only')
    parser.add_argument('--offline',action='store_true',help='Diagnostic only: skip game detection and global hotkey registration')
    args=parser.parse_args()
    if args.flow_check and not (args.offline and args.diagnose and args.reference):
        parser.error('--flow-check requires --offline --diagnose and --reference')
    if args.offline and not args.diagnose:
        parser.error('--offline requires --diagnose')
    if args.diagnose:
        import json
        from dataclasses import asdict
        from pathlib import Path
        import tkinter as tk
        from app.gui import RESOURCES
        from app.whitelist import load
        from app.inventory_recognition import preview
        from app.capture import reference,detect
        from app.input_control import Safety
        root=tk.Tk();root.withdraw();root.update();root.destroy()
        result={'tk':True,'whitelist_rows':len(load(RESOURCES/'app/default_whitelist.json')),'hotkey_registered':None,'candidate_windows':None,'background_input':'unverified','sent_keys':0,'offline':args.offline}
        if not args.offline:
            safety=Safety()
            result.update(hotkey_registered=safety.hotkey_ok,candidate_windows=len(detect()))
            safety.close()
        if args.reference:
            image,note=reference(args.reference)
            scanned=preview(image,load(RESOURCES/'app/default_whitelist.json'),RESOURCES/'scripts/ocr.ps1',args.mode)
            result.update(ocr_words=len(scanned.words),items=[x.__dict__ for x in scanned.detections],reference_note=note,mode=scanned.mode,scan_note=scanned.note,timings=scanned.timings,reviews=[asdict(x) for x in scanned.reviews])
        from app.fixed_batch import fixed_batch
        batch=fixed_batch(load(RESOURCES/'app/default_whitelist.json'))
        result['fixed_batch']={'materials':len(batch.materials),'completions':len(batch.completions),'requests':[asdict(x) for x in batch.materials]}
        if args.flow_check:
            from app.ocr_session import OcrSession
            from app.flow_vision import Vision
            with OcrSession(RESOURCES/'scripts/ocr.ps1') as session:
                screen=Vision(session).observe(image)
                result['flow']={'shared_storage':screen.storage(),'quantity_dialog':screen.quantity_dialog(),'submission':screen.submission(),'world':screen.world()}
        Path(args.diagnose).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        from app.gui import run
        run()
