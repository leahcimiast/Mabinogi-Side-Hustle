"""Reviewed exact OCR spellings shared by all three workflows.

Normalize exact observed spellings only; keep grades and plus markers distinct.
The player explicitly approved the standalone spelling 洋 for 洋蔥.
Quest callers must extract the material-name tail before using this table.
"""
MATERIAL_ALIASES = {
    '箾花': '箭花',
    '洋': '洋蔥',
    '洋蒽': '洋蔥',
    '洋悳': '洋蔥',
    '黄豆': '黃豆',
    '恘恘菇': '咻咻蘑菇',
}


def canonical_material(text):
    return MATERIAL_ALIASES.get(text,text)
