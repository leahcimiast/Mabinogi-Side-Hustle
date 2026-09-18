import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from PIL import Image
from app.flow_vision import Screen,MultiScreen,Label,tracker_identity,Vision
from app.automation import Runner
from app.fixed_batch import fixed_batch,Journal
from app.whitelist import load

def word(text,x=1135,y=235,w=115,h=20):return dict(text=text,x=x,y=y,w=w,h=h)
def report(y=282):return word('回報任務佈告欄',1160,y,108,14)

class TrackerRecognitionTests(unittest.TestCase):
    def setUp(self):self.image=Image.new('RGB',(1280,960))
    def test_missing_prefix_with_own_report_is_recognized(self):
        s=Screen(self.image,[word('鐵礦石'),report()])
        self.assertEqual(s.tracker('鐵礦石').text,'鐵礦石')
    def test_bare_name_requires_title_size_and_nearby_report(self):
        for words in [[word('鐵礦石')],[word('鐵礦石',h=14),report()],[word('鐵礦石'),report(y=420)]]:
            self.assertIsNone(Screen(self.image,words).tracker('鐵礦石'))
    def test_count_line_and_other_grade_are_not_title(self):
        for text in ['持有鐵礦石20/20','取得高級羊毛','取得高級原木+']:
            self.assertIsNone(Screen(self.image,[word(text),report()]).tracker('羊毛' if '羊毛' in text else '高級原木' if '原木' in text else '鐵礦石'))
    def test_prefix_changes_across_variants_keep_same_identity(self):
        s=MultiScreen(self.image,[[word('取得鐵礦石'),report()],[word('鐵礦石'),report()]])
        self.assertEqual(tracker_identity(s.tracker('鐵礦石').text),'鐵礦石')
    def test_two_different_tracker_rows_are_ambiguous(self):
        s=MultiScreen(self.image,[[word('取得鐵礦石')],[word('取得鐵礦石',y=340)]])
        with self.assertRaises(RuntimeError):s.tracker('鐵礦石')
    def test_duplicate_title_in_same_observation_stops(self):
        s=Screen(self.image,[word('取得鐵礦石'),word('取得鐵礦石',y=340)])
        self.assertIsNone(s.tracker('鐵礦石'))

    def test_completion_identity_does_not_use_substring_matching(self):
        region=(400,480,900,570)
        for text,identity,expected in [('取得鐵礦石','鐵礦石',True),('鐵礦石','取得鐵礦石',True),('取得高級鐵礦石','鐵礦石',False),('取得高級原木+','高級原木',False)]:
            s=MultiScreen(self.image,[[],[word(text,500,510,200,20)]])
            self.assertEqual(s.quest_identity_present(identity,region),expected)

    def test_partly_read_action_prefixes_with_pin_marks(self):
        for prefix in ['得','取','製','作']:
            s=MultiScreen(self.image,[[word(prefix+'鐵礦石'),report()],[word(prefix+'鐵礦石~'),report()]])
            self.assertEqual(tracker_identity(s.tracker('鐵礦石').text),'鐵礦石')
    def test_partial_prefix_still_needs_own_report(self):
        self.assertIsNone(Screen(self.image,[word('得鐵礦石')]).tracker('鐵礦石'))
    def test_partial_prefix_does_not_erase_grade_or_plus(self):
        for text in ['得高級鐵礦石','得鐵礦石+']:
            self.assertIsNone(Screen(self.image,[word(text),report()]).tracker('鐵礦石'))
        s=MultiScreen(self.image,[[word('得鐵礦石'),report()],[word('得高級鐵礦石'),report()]])
        with self.assertRaises(RuntimeError):s.tracker('鐵礦石')

    def test_split_action_fragment_does_not_veto_complete_title(self):
        good=[word('取得鐵礦石'),report()]
        split=[word('取得',1135,235,41,20),word('礦石~',1201,235,60,20)]
        screen=MultiScreen(self.image,[good,good,good,good,split])
        self.assertEqual(tracker_identity(screen.tracker('鐵礦石').text),'鐵礦石')
        self.assertIsNone(MultiScreen(self.image,[split]).tracker('鐵礦石'))
    def test_bulleted_other_grade_remains_a_conflict(self):
        screen=MultiScreen(self.image,[[word('取得鐵礦石'),report()],
                                      [word('·取得高級鐵礦石'),report()]])
        with self.assertRaisesRegex(RuntimeError,'高級鐵礦石'):screen.tracker('鐵礦石')

    def test_report_word_order_and_missing_action_prefix(self):
        for text in ['回報任務佈告欄','向任務佈告欄回報']:
            words=[word('箭花'),word(text,1150,282,115,14)]
            for screen in [Screen(self.image,words),MultiScreen(self.image,[[],words])]:
                self.assertIsNotNone(screen.report())
                self.assertIsNotNone(screen.tracker('箭花'))
    def test_board_name_without_report_is_not_ready(self):
        for text in ['前往任務佈告欄','向其他人回報']:
            screen=Screen(self.image,[word('箭花'),word(text,1150,282,115,14)])
            self.assertIsNone(screen.report());self.assertIsNone(screen.tracker('箭花'))

    def test_spider_search_title_uses_whitelist_material_mapping(self):
        entries=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
        quest=next(q for q in entries if '蜘蛛絲' in q.quest)
        screen=Screen(self.image,[word('尋找蜘蛛網'),report()])
        self.assertEqual(tracker_identity(Runner.expected_tracker(None,screen,quest).text),'蜘蛛網')
        self.assertIsNone(screen.tracker('蜘蛛絲'))
        conflict=MultiScreen(self.image,[[word('尋找蜘蛛網'),report()],[word('尋找高級蜘蛛網'),report()]])
        with self.assertRaises(RuntimeError):conflict.tracker('蜘蛛網')

    def test_tracker_ocr_crops_quadrant_and_maps_click_coordinates(self):
        session=Mock();session.recognize_many.return_value=[[
            dict(text='尋找蜘蛛網',x=520,y=250,w=100,h=20),
            dict(text='回報任務佈告欄',x=520,y=297,w=120,h=15)],[]]
        screen=Vision(session).observe_tracker(self.image)
        images=session.recognize_many.call_args.args[0]
        self.assertEqual([im.size for im in images],[(680,520),(1320,1000)])
        self.assertEqual(screen.tracker('蜘蛛網').point,(1190,240))
        self.assertIsNotNone(screen.report())

    def test_shorter_title_fragment_does_not_veto_exact_reading(self):
        exact=[word('尋找蜘蛛網'),report()]
        fragment=[word('尋找蜘',1135,235,62,20)]
        self.assertIsNotNone(MultiScreen(self.image,[exact,fragment]).tracker('蜘蛛網'))
        self.assertIsNone(MultiScreen(self.image,[fragment]).tracker('蜘蛛網'))
        for text in ['尋找蜘蛛絲','製作蜘']:
            with self.assertRaises(RuntimeError):
                MultiScreen(self.image,[exact,[word(text,1135,235,62,20)]]).tracker('蜘蛛網')
    def test_full_width_conflict_and_plus_are_not_fragments(self):
        with self.assertRaises(RuntimeError):
            MultiScreen(self.image,[[word('尋找蜘蛛網'),report()],[word('尋找蜘')]]).tracker('蜘蛛網')
        with self.assertRaises(RuntimeError):
            MultiScreen(self.image,[[word('取得高級原木+'),report()],[word('取得高級原木',1135,235,90,20)]]).tracker('高級原木+')
    def test_pin_comma_does_not_change_exact_identity(self):
        screen=MultiScreen(self.image,[[word('尋找蜘蛛網,'),report()],[word('·尋找蜘蛛網'),report()]])
        self.assertEqual(tracker_identity(screen.tracker('蜘蛛網').text),'蜘蛛網')

    def test_report_only_ignores_title_noise_but_rejects_two_report_rows(self):
        screen=MultiScreen(self.image,[[word('尋找蜘'),report()],
                                      [word('尋找蜘蛛網,'),report()]])
        self.assertIsNotNone(screen.report())
        with self.assertRaisesRegex(RuntimeError,'多個'):
            MultiScreen(self.image,[[report(),report(y=400)]]).report()

    def test_report_accepts_noisy_task_word_with_exact_board_and_report(self):
        for text in ['回報壬務佈告欄','向佈告欄回報']:
            self.assertIsNotNone(Screen(self.image,[word(text,1150,282,115,15)]).report())
        self.assertIsNone(Screen(self.image,[word('佈告欄',1150,282,115,15)]).report())
    def test_tracker_retries_only_missing_report_and_world_regions(self):
        session=Mock();session.recognize_many.side_effect=[ [[],[],[],[]],
            [[dict(text='回報壬務佈告欄',x=140,y=80,w=100,h=15)],[],[],[],[],
             [dict(text='對周圍說話',x=140,y=100,w=90,h=18)],[],[],[],[]] ]
        screen=Vision(session).observe_tracker(self.image,include_world=True)
        self.assertIsNotNone(screen.report());self.assertTrue(screen.world())
        self.assertEqual(session.recognize_many.call_count,2)

    def test_three_character_report_cues_are_shared_and_region_limited(self):
        for text in ('告回報','佈回報','欄回報','向務告回報','回報告'):
            with self.subTest(text=text):
                self.assertIsNotNone(Screen(self.image,[word(text,1200,282,65,14)]).report())
                self.assertIsNone(Screen(self.image,[word(text,500,282,65,14)]).report())
        for text in ('回報','報報報','向其他人回報','佈告欄','持有貝類10/10'):
            self.assertIsNone(Screen(self.image,[word(text,1130,282,135,14)]).report())
        with self.assertRaisesRegex(RuntimeError,'多個'):
            MultiScreen(self.image,[[word('告回報',1200,282,65,14),
                                    word('欄回報',1200,400,65,14)]]).report()

class TrackerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        entries=load(Path(__file__).resolve().parents[1]/'app/default_whitelist.json')
        self.journal=Journal(Path(self.temp.name)/'batch.json',fixed_batch(entries))
        self.r=Runner(Mock(),Mock(),Mock(),self.journal,entries,Path('scripts/ocr.ps1'))
        self.r.click=Mock();self.r.find_scroll=Mock();self.r.wait_use_button=Mock()
        self.screen=Mock();self.screen.world.return_value=True
        self.screen.tracker.return_value=Label('鐵礦石',(1185,235,1250,255))
        self.screen.report.return_value=Label('回報任務佈告欄',(1160,282,1268,296))
        self.r.screen=Mock(side_effect=[self.screen,RuntimeError('submission reached')])
        self.r.expected_tracker=lambda screen,q:screen.tracker(q.material) if q.quest==entries[0].quest else None
    def tearDown(self):self.temp.cleanup()
    def test_ready_existing_current_quest_is_adopted_without_scroll_use(self):
        with self.assertRaisesRegex(RuntimeError,'submission reached'):self.r.quests()
        self.r.find_scroll.assert_not_called();self.r.wait_use_button.assert_not_called()
        self.assertEqual(self.journal.data['active']['identity'],'鐵礦石')
        self.assertEqual(self.journal.data['completed'],0)
        self.r.click.assert_called_once_with((1214,289))
    def test_unmatched_existing_report_cannot_activate_another_quest(self):
        self.screen.tracker.return_value=None
        with self.assertRaisesRegex(RuntimeError,'身份不明'):self.r.quests()
        self.r.find_scroll.assert_not_called();self.r.click.assert_not_called()
        self.assertIsNone(self.journal.data['active'])
    def test_unresolved_activation_still_requires_reconciliation(self):
        self.journal.begin('activate',{'index':0,'identity':None})
        with self.assertRaisesRegex(RuntimeError,'結果未確認'):self.r.quests()
        self.r.screen.assert_not_called();self.r.find_scroll.assert_not_called()

    def test_other_quests_report_row_does_not_authorize_adoption(self):
        self.screen.report.return_value=Label('回報任務佈告欄',(1160,420,1268,435))
        with self.assertRaisesRegex(RuntimeError,'身份不明'):self.r.quests()
        self.r.find_scroll.assert_not_called();self.r.click.assert_not_called()
    def test_known_active_quest_does_not_reread_title(self):
        self.journal.data['active']={'index':0,'identity':'取得鐵礦石'}
        self.screen.tracker.side_effect=AssertionError('No title OCR after identity is recorded')
        with self.assertRaisesRegex(RuntimeError,'submission reached'):self.r.quests()
        self.screen.tracker.assert_not_called()
        self.r.click.assert_called_once_with(self.screen.report.return_value.point)
        self.assertEqual(self.journal.data['completed'],0)

    def test_ready_report_does_not_require_chat_text(self):
        self.screen.world.return_value=False
        with self.assertRaisesRegex(RuntimeError,'submission reached'):self.r.quests()
        self.r.find_scroll.assert_not_called()
        self.r.click.assert_called_once_with(self.screen.report.return_value.point)
