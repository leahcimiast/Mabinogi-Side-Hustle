"""OCR previews cannot become executable plans in this milestone."""
def build_plan(*args, **kwargs):
    raise NotImplementedError('Preparation planning is not enabled in milestone 1')
