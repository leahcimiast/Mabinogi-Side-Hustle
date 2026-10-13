"""Retrieval batching preserves every alternate reading and isolated retry."""
import unittest
from unittest.mock import Mock
from PIL import Image
from app.flow_vision import Vision
import test_fixed_batch as fixtures


def words(first='羊毛',scale=1):
    return [dict(text=text,x=(20+400*i)*scale,y=20*scale,
                 w=70*scale,h=25*scale)
            for i,text in enumerate((first,'玉米','小麥','雞蛋','馬鈴薯','箭花'))]


def methods():
    return [words(),words('高級羊毛',.5),words('羊毛+'),words(),words(scale=.5)]


class StorageNameBatchTests(unittest.TestCase):
    def setUp(self):
        self.image=Image.new('RGB',(1280,960))
        self.session=Mock()
        self.vision=Vision(self.session)
        self.vision._geometry_image=self.image
        self.vision._geometry_tops=[350]

    def test_all_five_methods_keep_conflicting_grades_and_plus_markers(self):
        self.session.recognize_many.return_value=methods()
        first=self.vision.storage_names(self.image,batch=True)
        extra=self.vision.storage_names_retry(self.image)
        self.assertEqual(first[0].text,'羊毛')
        self.assertEqual({x.text for x in extra if x.box[0]==57},
                         {'羊毛','高級羊毛','羊毛+'})
        self.assertTrue(all(x.box==(57,285,151,345)
                            for x in extra if x.box[0]==57))
        self.session.recognize_many.assert_called_once()
        self.assertEqual([im.size for im in self.session.recognize_many.call_args.args[0]],
                         [(2400,180),(1200,90),(2400,180),(2400,180),(1200,90)])
        self.assertIsNone(self.vision._storage_name_pending)

    def test_initial_only_reading_still_receives_original_isolated_retry(self):
        readings=methods()
        for i in range(1,5):readings[i]=readings[i][1:]
        isolated=[dict(text='羊毛',x=40,y=30,w=50,h=26)]
        self.session.recognize_many.side_effect=[readings,[isolated]]
        self.vision.storage_names(self.image,batch=True)
        extra=self.vision.storage_names_retry(self.image)
        self.assertTrue(any(x.text=='羊毛' and x.box[0]==57 for x in extra))
        self.assertEqual([len(c.args[0]) for c in self.session.recognize_many.call_args_list],[5,1])
        self.assertEqual(self.session.recognize_many.call_args.args[0][0].size,(228,100))

    def test_identical_text_in_different_cells_is_not_deduplicated(self):
        readings=methods()
        for reading in readings:reading[1]['text']='羊毛'
        self.session.recognize_many.return_value=readings
        self.vision.storage_names(self.image,batch=True)
        extra=self.vision.storage_names_retry(self.image)
        self.assertEqual({x.box[0] for x in extra if x.text=='羊毛'},{57,152})

    def test_new_snapshot_cannot_reuse_previous_alternate_evidence(self):
        self.session.recognize_many.return_value=methods()
        self.vision.storage_names(self.image,batch=True)
        other=self.image.copy()
        self.vision._geometry_image=other
        self.vision._geometry_tops=[350]
        self.session.reset_mock()
        self.session.recognize_many.side_effect=[[words('牛奶',s)] for s in (.5,1,1,.5)]
        extra=self.vision.storage_names_retry(other)
        self.assertEqual(self.session.recognize_many.call_count,4)
        self.assertEqual({x.text for x in extra if x.box[0]==57},{'牛奶'})
        self.assertIsNone(self.vision._storage_name_pending)

    def test_pending_results_can_only_be_consumed_once(self):
        self.session.recognize_many.return_value=methods()
        self.vision.storage_names(self.image,batch=True)
        self.vision.storage_names_retry(self.image)
        self.session.reset_mock()
        self.session.recognize_many.side_effect=[[words(scale=s)] for s in (.5,1,1,.5)]
        self.vision.storage_names_retry(self.image)
        self.assertEqual(self.session.recognize_many.call_count,4)

    def test_new_request_discards_old_evidence_even_when_ocr_fails(self):
        self.session.recognize_many.return_value=methods()
        self.vision.storage_names(self.image,batch=True)
        self.session.recognize_many.side_effect=RuntimeError('OCR cancelled')
        with self.assertRaisesRegex(RuntimeError,'cancelled'):
            self.vision.storage_names(self.image,batch=True)
        self.assertIsNone(self.vision._storage_name_pending)

    def test_incomplete_batch_is_error_not_partial_evidence(self):
        self.session.recognize_many.return_value=methods()[:4]
        with self.assertRaisesRegex(RuntimeError,'batch size'):
            self.vision.storage_names(self.image,batch=True)
        self.assertIsNone(self.vision._storage_name_pending)

    def test_blank_snapshot_does_not_replay_geometry_or_imply_any_item(self):
        self.vision._storage_name_boxes=Mock(return_value=[])
        self.vision._storage_boxes=[]
        self.assertEqual(self.vision.storage_names(self.image,batch=True),[])
        self.assertEqual(self.vision.storage_names_retry(self.image),[])
        self.vision._storage_name_boxes.assert_called_once_with(self.image)
        self.session.recognize_many.assert_not_called()

    def test_crop_and_gray_preparation_is_shared_within_batch(self):
        # One raw crop per cell plus one wider crop per cell, rather than five raw crops.
        crop=self.image.crop
        self.image.crop=Mock(wraps=crop)
        self.session.recognize_many.return_value=methods()
        self.vision.storage_names(self.image,batch=True)
        self.assertEqual(self.image.crop.call_count,12)


class RetrievalBatchSafetyTests(unittest.TestCase):
    setUp=fixtures.WithdrawalTests.setUp
    tearDown=fixtures.WithdrawalTests.tearDown

    def test_first_tab_requests_batch_but_keeps_alternate_checks(self):
        self.runner.withdrawal()
        self.runner.vision.storage_names.assert_called_once_with(self.screen.image,batch=True)
        self.runner.vision.storage_names_retry.assert_called_once_with(self.screen.image)

    def test_batch_error_never_selects_or_transfers_material(self):
        self.runner.vision.storage_names.side_effect=RuntimeError('OCR batch failed')
        with self.assertRaisesRegex(RuntimeError,'batch failed'):
            self.runner.withdrawal()
        self.runner.click.assert_not_called()
        self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
        self.assertNotIn('鐵礦石',self.j.data['withdrawn'])

    def test_stop_after_name_evidence_never_selects_material(self):
        self.safety.check.side_effect=RuntimeError('F8 / focus lost')
        with self.assertRaisesRegex(RuntimeError,'F8'):
            self.runner.withdrawal()
        self.runner.click.assert_not_called()
        self.safety.click.assert_not_called()
        self.assertIsNone(self.j.data['pending'])
        self.assertNotIn('鐵礦石',self.j.data['withdrawn'])


if __name__=='__main__':unittest.main()
