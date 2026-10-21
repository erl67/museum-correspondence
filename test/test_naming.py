from copy import deepcopy
from unittest.mock import patch

from correspondence.discovery import discover
from correspondence.execution import Quota, transcribe
from correspondence.exports import export_all
from correspondence.naming import canonical_stem, filename_hints, split_page
from correspondence.plaintext import title
from correspondence.publication import publish_text
from correspondence.relocation import reconcile_paths
from correspondence.review import current_records
from .helpers import Clock, FakeTransport, Workspace, jpeg, response


class NamingTests(Workspace):
    def test_compact_dates_partial_dates_and_unknown(self):
        for token, expected in [('18990807', '1899-08-07'), ('189908', '1899-08'),
                                ('1899', '1899'), ('undated', None),
                                ('1899-8-7', '1899-08-07')]:
            with self.subTest(token=token):
                self.assertEqual(filename_hints('Shufeldt,P-Todd-' + token)['date'], expected)
        for token in ('18990229', '189913', '18990000', '0000', '1899080'):
            self.assertEqual(filename_hints('A-B-' + token), {})
        self.assertEqual(canonical_stem('A-B-1899-8-7-a'), 'A-B-18990807-a')

    def test_numeric_order_including_tenth_page(self):
        self.setup_letter(tuple(f'A-B-18990807_{n:02d}.jpg' for n in range(1, 12)))
        images = {i['image_id']: i for i in self.inventory['images']}
        self.assertEqual([images[i]['filename'] for i in self.letter['image_ids']],
                         [f'A-B-18990807_{n:02d}.jpg' for n in range(1, 12)])
        self.assertEqual(self.letter['grouping'], 'provisional')
        self.assertEqual(self.letter['hints']['date'], '1899-08-07')

    def test_same_date_letter_suffixes_stay_separate(self):
        self.setup_letter(('A-B-18990807-a_01.jpg', 'A-B-18990807-a_02.jpg',
                           'A-B-18990807-b_01.jpg'))
        self.assertEqual([len(l['image_ids']) for l in self.inventory['letters']], [2, 1])
        self.assertTrue(all(l['grouping'] == 'provisional' for l in self.inventory['letters']))

    def test_gaps_zero_and_duplicate_numeric_labels_need_review(self):
        for names in [('A-B-1899_01.jpg', 'A-B-1899_03.jpg'),
                      ('A-B-1899_00.jpg',),
                      ('A-B-1899_01.jpg', 'A-B-1899_1.jpeg'),
                      ('A-B-1899_01.jpg', 'A-B-1899(1).jpg')]:
            with self.subTest(names=names):
                folder = self.inputs / str(len(list(self.inputs.iterdir())))
                for name in names:
                    jpeg(folder / name)
                inv = discover(folder)
                self.assertEqual(inv['letters'][0]['grouping'], 'needs_review')

    def test_partial_and_undated_letters_are_groupable(self):
        self.setup_letter(('A-B-189908_01.jpg', 'A-B-undated_01.jpg'))
        self.assertTrue(all(l['grouping'] == 'provisional' for l in self.inventory['letters']))
        self.assertEqual(split_page('A-B-1899(AB)'), ('A-B-1899', 'AB'))
        self.assertEqual(split_page('A-B-1899_01'), ('A-B-1899', '01'))

    def test_titles_drop_page_and_compact_dates_but_preserve_custom_titles(self):
        self.setup_letter(('A-B-18990807_01.jpg',))
        images = {i['image_id']: i for i in self.inventory['images']}
        self.assertEqual(title(self.letter, images), 'A-B-18990807')
        self.letter['override'] = {'title': 'A-B-1899-08-07'}
        self.assertEqual(title(self.letter, images), 'A-B-18990807')
        self.letter['override']['title'] = 'Staff title 2'
        self.assertEqual(title(self.letter, images), 'Staff title 2')

    def test_migration_preserves_completed_reading_order_ids_and_history(self):
        self.setup_letter(('A-B-1899-05-02(1).jpg', 'A-B-1899-05-02(2).jpg'))
        clock = Clock()
        transcribe(self.store, self.letter, self.request, self.config,
                   lambda: FakeTransport([response(self.doc)]),
                   quota=Quota(self.config, clock.time, clock.sleep))
        old = self.store.journal.read_bytes()
        results = deepcopy(self.store.results())
        paths = {i['path']: f'A-B-18990502_{n:02d}.jpg'
                 for n, i in enumerate(self.inventory['images'], 1)}
        for source, target in paths.items():
            (self.inputs / source).rename(self.inputs / target)
        updated = reconcile_paths(self.inventory, dict(version=1, source='Staff approved naming migration', paths=paths))
        refreshed = discover(self.inputs, updated)
        self.assertEqual(refreshed['letters'][0]['letter_id'], self.letter['letter_id'])
        self.assertEqual(refreshed['letters'][0]['image_ids'], self.letter['image_ids'])
        self.assertEqual(refreshed['letters'][0]['hints']['date'], '1899-05-02')
        self.store.append('inventory', refreshed)
        self.assertTrue(self.store.journal.read_bytes().startswith(old))
        self.assertEqual(self.store.results(), results)
        record = current_records(self.store, refreshed)[0]
        self.assertEqual(record['execution'], 'complete')
        self.assertEqual(record['document'], self.doc)
        with patch('correspondence.provider.Gemini.send', side_effect=AssertionError('network forbidden')):
            output = self.root / 'exports'
            export_all(self.store, refreshed, output)
            publish_text(self.store, refreshed, output)
        text = (self.inputs / 'A-B-18990502.txt').read_text(encoding='utf-8')
        for name in paths.values():
            self.assertIn(name, text)
        for name in paths:
            self.assertNotIn(name, text)
