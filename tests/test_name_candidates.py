"""Name suggestions used by the command-line diagnostic preview."""
import unittest
from app.name_candidates import suggest,make_review
from app.recognition import Detection
from app.whitelist import validate
Q=validate([('採集卷軸: 小麥','小麥',10),('採集卷軸: 咻咻蘑菇','咻咻蘑菇',20),('採礦卷軸: 鐵礦石','鐵礦石',20),('採集卷軸: 高級原木+','高級原木+',20),('採集卷軸: 蜘蛛絲','蜘蛛網',10),('料理卷軸: 蘋果汁','蘋果汁',5)])
class NameCandidateTests(unittest.TestCase):
    def test_typo_and_missing_prefix_character_suggest_only(self):
        self.assertEqual(suggest('採集卷:小麥',Q)[0].name,'採集卷軸: 小麥')
        self.assertEqual(suggest('採集卷軸:咻咻磨菇',Q)[0].name,'採集卷軸: 咻咻蘑菇')
    def test_plus_changes_identity(self):
        self.assertEqual(suggest('採集卷軸:高級原木',Q),[])
        self.assertEqual(suggest('採集卷軸:小麥+',Q),[])
    def test_type_conflict_needs_explicit_check(self):
        c=suggest('採集卷軸:鐵礦石',Q)[0]
        self.assertEqual(c.name,'採礦卷軸: 鐵礦石')
        self.assertTrue(c.type_conflict)
        self.assertEqual(suggest('採集卷軸:鐵礦',Q),[])
    def test_material_alone_and_nonwhitelisted_food_have_no_suggestion(self):
        for raw in ['小麥','料理卷軸:蒸蛤蜊','採集卷軸:不可交易','范·戈斯特的羅盤']:
            self.assertEqual(suggest(raw,Q),[])
    def test_material_mapping_not_used_for_suggestion(self):
        c=suggest('採集卷軸:蜘蛛綵',Q)[0]
        self.assertEqual(c.name,'採集卷軸: 蜘蛛絲')
        self.assertEqual(Q[4].material,'蜘蛛網')
    def test_close_candidates_stay_ambiguous(self):
        entries=validate([('採集卷軸: 紅蘑菇','紅蘑菇',1),('採集卷軸: 白蘑菇','白蘑菇',1)])
        item=Detection('未確認卷軸',None,(0,0,96,40),'','unconfirmed','採集卷軸:灰蘑菇')
        review=make_review(0,item,3,entries)
        self.assertTrue(review.ambiguous)
        self.assertFalse(review.can_accept)


if __name__=='__main__':unittest.main()
