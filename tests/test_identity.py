import contextlib
import io
import json
import tempfile
import unittest
import base64
import re
from pathlib import Path
from unittest.mock import patch

from mcd_life_kit.annual_report import render_html, summarize
from mcd_life_kit.cli import main
from mcd_life_kit.identity import RULES, make_identity, resolve_gender, taste_scores
from mcd_life_kit.visuals import generate_visual, render_visual
from mcd_life_kit.portraits import portrait_path


def base():
    return summarize([], 2026, demo=True)


class IdentityTests(unittest.TestCase):
    def test_each_realm_boundary_and_orders_uncapped(self):
        for tier in RULES['tiers']:
            minimum = tier['minimum']
            # 每个可达门槛与前一分，验证最高匹配档位。
            for target in {minimum, max(0, minimum-1)}:
                orders, month = divmod(target, 2)
                report = dict(base(), count=orders, months=[month]+[0]*11)
                result = make_identity(report)
                expected = max(t['level'] for t in RULES['tiers'] if target >= t['minimum'])
                self.assertEqual(result['level'], expected)
                self.assertEqual(result['score'], target)
        high = make_identity(dict(base(), count=999, months=[1]*12, unique_foods=999))
        self.assertEqual(high['score'], 999*2+12+12)
        self.assertEqual(high['level'], 8)

    def test_gender_changes_title_not_merit(self):
        report = dict(base(), count=1, days=1, months=[1]+[0]*11, unique_foods=1)
        male, female = [make_identity(report, g) for g in ['male','female']]
        self.assertEqual(male['title'], '见习小师弟')
        self.assertEqual(female['title'], '见习小师妹')
        self.assertEqual(make_identity(report), dict(male, gender_source='default'))
        self.assertEqual({i['score'] for i in [male,female]}, {4})
        self.assertEqual({i['sect'] for i in [male,female]}, {'逍遥门'})
        with self.assertRaises(ValueError):
            make_identity(report, 'neutral')

    def test_final_realm_starts_at_160_and_is_named_true_god_for_both(self):
        report = dict(base(), count=79, months=[1]+[0]*11, unique_foods=0)
        below = make_identity(report)
        self.assertEqual(below['score'], 159)
        self.assertEqual(below['level'], 7)
        for gender in ['male','female']:
            final = make_identity(dict(report, unique_foods=1), gender)
            self.assertEqual(final['score'], 160)
            self.assertEqual(final['level'], 8)
            self.assertEqual(final['title'], '麦门真神')
            higher = make_identity(dict(report, count=365), gender)
            self.assertEqual(higher['title'], '麦门真神')
            self.assertGreater(higher['score'], 160)

    def test_no_spend_rank_or_gender_guess(self):
        report = dict(base(), days=3, unique_foods=5, months=[1]+[0]*11)
        self.assertEqual(make_identity(dict(report, amount='0')), make_identity(dict(report, amount='999999')))
        self.assertEqual(resolve_gender(None, {'gender': 'female'}), ('female', 'account'))
        self.assertEqual(resolve_gender('male', {'gender':'female'}), ('male','user'))
        self.assertEqual(resolve_gender(None, {'gender':2}), ('male','default'))
        self.assertEqual(resolve_gender(None, {'address':{'gender':'female'}}), ('male','default'))

    def test_same_day_multiple_completed_orders_count_and_duplicates_do_not(self):
        from test_annual_report import order
        one = summarize([order('a')], 2026)
        three = summarize([order('a'),order('b'),order('c'),order('a'),order('d',orderStatus='已取消')], 2026)
        self.assertEqual(one['days'], three['days'])
        self.assertEqual(three['count'], 3)
        self.assertEqual(make_identity(three)['score']-make_identity(one)['score'], 4)
        self.assertEqual(make_identity(three)['score_components']['orders'], 6)

    def test_low_frequency_sample_is_sweeper(self):
        report = dict(base(), count=9, days=9, months=[0,0,1,0,2,3,1,1,1,0,0,0], unique_foods=15)
        identity = make_identity(report)
        self.assertEqual(identity['score'], 36)
        self.assertEqual(identity['title'], '藏味扫地僧')
        self.assertEqual(identity['score_components'], {'orders':18,'months':6,'variety':12})

    def test_all_foods_not_top_five_and_single_classification(self):
        foods = {'薯条':2,'鸡腿堡':1,'可乐':2,'咖啡':1,'新地':1,'鸡块':1}
        scores = taste_scores(foods)
        self.assertEqual(scores['burger'], 1)
        self.assertEqual(scores['chicken'], 1)
        self.assertEqual(sum(scores.values()), sum(foods.values()))
        identity = make_identity(dict(base(), taste_scores=scores))
        self.assertEqual(identity['sect'], '薯山剑派')

    def test_all_ranks_share_exact_portrait_and_avatar_original(self):
        for gender in ['male', 'female']:
            for tier in RULES['tiers']:
                report = base()
                report['identity'] = dict(make_identity(report, gender), level=tier['level'])
                source = portrait_path(report['identity'])
                self.assertEqual(source.parent.name, f'{gender}-v1')
                manifest = json.loads((source.parent/'manifest.json').read_text())
                self.assertEqual(source.name, next(row['file'] for row in manifest['images'] if row['level']==tier['level']))
                expected = source.read_bytes()
                for page in [render_html(report), render_visual(report, None, 'identity-card'), render_visual(report, None, 'avatar')]:
                    encoded = re.search(r'class="character-image" src="data:image/png;base64,([^"]+)"', page)[1]
                    self.assertEqual(base64.b64decode(encoded), expected)
                with tempfile.TemporaryDirectory() as tmp:
                    with patch('mcd_life_kit.visuals.subprocess.run', side_effect=AssertionError('avatar must not need screenshot')):
                        _, image = generate_visual(report, Path(tmp), None, 'avatar')
                    self.assertEqual(image.read_bytes(), expected)

    def test_custom_portrait_shared_by_entire_cli_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = portrait_path(make_identity(base(), 'female'))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['all', '--mock', '--year', '2026', '--html-only', '--output', tmp,
                                       '--portrait-image', str(source), '--file-suffix', 'shared']), 0)
            for kind in ['annual-report', 'identity-card', 'avatar']:
                page = (Path(tmp)/f'{kind}_shared.html').read_text()
                encoded = re.search(r'class="character-image" src="data:image/png;base64,([^"]+)"', page)[1]
                self.assertEqual(base64.b64decode(encoded), source.read_bytes())
            self.assertEqual((Path(tmp)/'avatar_shared.png').read_bytes(), source.read_bytes())
            self.assertFalse((Path(tmp)/'avatar_shared.svg').exists())

    def test_placeholder_text_cannot_break_generated_page(self):
        report = base()
        report['identity'] = make_identity(report)
        from mcd_life_kit.visuals import render_visual
        nickname = '__IDENTITY_AVATAR____CARD_AVATAR__</script>'
        annual = render_html(report, nickname)
        data = annual.split('<script id="report-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(data)['nickname'], nickname)
        card = render_visual(report, nickname, 'identity-card')
        self.assertIn('__CARD_AVATAR__&lt;/script&gt;', card)
        self.assertEqual(card.count('class="character-image"'), 1)

    def test_shared_identity_and_optional_ai_only_brief(self):
        report = base()
        report['identity'] = make_identity(report, 'female')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for kind in ['identity-card','avatar']:
                generate_visual(report, output, '测试昵称', kind, png=False)
                result = (output/f'{kind}.html').read_text()
                self.assertIn(report['identity']['serial'], result)
                self.assertIn(report['identity']['title'], result)
                self.assertNotIn('__TITLE__', result)
            self.assertFalse((output/'avatar-ai-brief.md').exists())
            generate_visual(report, output, '测试昵称', 'avatar', png=False, ai_brief=True)
            self.assertTrue((output/'avatar-ai-brief.md').exists())
            self.assertIn(report['identity']['serial'], render_html(report))
            self.assertEqual(json.loads((output/'identity.json').read_text()), report['identity'])

    def test_no_intent_menu_does_not_read_account(self):
        with patch.dict('os.environ', {'MCD_MCP_TOKEN':'configured-test-token'}, clear=True), \
             patch('mcd_life_kit.cli.load_env'), \
             patch('mcd_life_kit.cli.collect_orders', side_effect=AssertionError('must not query')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([]), 0)
            self.assertIn('麦门年报', output.getvalue())
            self.assertIn('性别称谓', output.getvalue())


if __name__ == '__main__':
    unittest.main()
