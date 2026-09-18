import unittest
from unittest.mock import Mock
from PIL import Image
from app.whitelist import load
from app.stock_check import StockVision
from app.ocr_aliases import canonical_material
from app.inventory_recognition import match_scroll_tail,scroll_label_candidates

class SharedAliasesTests(unittest.TestCase):
    def test_whole_names_are_consistent_for_material_and_quest_scanners(self):
        entries=load('app/default_whitelist.json');reader=StockVision(Mock(),entries)
        for raw,expected in [('箾花','箭花'),('洋','洋蔥'),('洋蒽','洋蔥'),('洋悳','洋蔥'),('黄豆','黃豆')]:
            self.assertEqual(canonical_material(raw),expected)
            self.assertEqual(reader.resolve_name({raw}),expected)
            quest=next(q.quest for q in entries if q.material==expected)
            self.assertEqual(match_scroll_tail('採集卷軸:'+raw,entries),quest)
        for raw in ('洋+','洋悳+','高級洋悳','海洋','箾花+','高級箾花'):
            self.assertIsNone(reader.resolve_name({raw}))
            self.assertIsNone(match_scroll_tail('採集卷軸:'+raw,entries))

    def test_unrecognized_label_uses_targeted_retry(self):
        entries=load('app/default_whitelist.json')
        quest=next(q.quest for q in entries if q.material=='洋蔥')
        def word(text):return {'text':text,'x':45,'y':45,'w':70,'h':30}
        class Session:
            def __init__(self):self.calls=0
            def recognize_many(self,images):
                self.calls+=1
                if self.calls==1:return [[word('採集卷軸:蒽')]]+[[] for _ in images[1:]]
                if self.calls<=3:return [[] for _ in images]
                return [[word('採集卷軸:洋悳')],[word('採集卷軸:洋悳')]]
        found=scroll_label_candidates(Image.new('RGB',(1280,960)),quest,entries,Session())
        self.assertEqual(len(found),1)
        self.assertEqual(found[0][1],'採集卷軸:洋悳')
