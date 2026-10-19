import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcd_life_kit.annual_report import artifact_stem, generate_report, summarize
from mcd_life_kit.cli import main
from mcd_life_kit.identity import make_identity
from mcd_life_kit.mcp_client import read_token_file
from mcd_life_kit.profile import account_name, choose_display_name, fetch_account_name
from mcd_life_kit.visuals import generate_visual, render_visual


class ProfileTests(unittest.TestCase):
    def test_only_explicit_account_names_are_used(self):
        self.assertEqual(account_name({'code':200,'data':{'userInfo':{'nickName':'  麦麦用户  '}}}), '麦麦用户')
        self.assertIsNone(account_name({'data':{'accountId':'123456','availablePoint':'100'}}))
        self.assertIsNone(account_name({'data':{'address':{'contactName':'配送联系人'}}}))
        self.assertIsNone(account_name({'data':{'userName':'13812345678'}}))
        self.assertIsNone(account_name({'data':{'userName':'138****5678'}}))
        self.assertIsNone(account_name({'success':False,'data':{'nickname':'不可用'}}))

    def test_name_precedence_and_normal_anonymous_default(self):
        self.assertEqual(choose_display_name(None,'账号昵称','example'), ('账号昵称','account'))
        self.assertEqual(choose_display_name(None,None,'example'), ('example','fallback'))
        self.assertEqual(choose_display_name(None,None), (None,'hidden'))
        self.assertEqual(choose_display_name('指定名','账号昵称','example'), ('指定名','user'))
        self.assertEqual(choose_display_name('', '账号昵称'), (None,'hidden'))

    def test_account_lookup_uses_only_available_read_tools(self):
        class Fake:
            calls=[]
            def call_tool(self,name,args):
                self.calls.append((name,args))
                return {'data':{'nickname':'接口昵称'}}
        client=Fake()
        self.assertIsNone(fetch_account_name(client,[]))
        self.assertEqual(fetch_account_name(client,[{'name':'query-my-account','inputSchema':{'properties':{}}}]), '接口昵称')
        self.assertEqual(client.calls,[('query-my-account',{})])

    def test_account_file_never_uses_other_account_environment(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'MCD_MCP_TOKEN':'other-account-token'}):
            path=Path(tmp)/'.env_example'
            path.write_text('MCD_MCP_TOKEN=selected-account-token\n')
            self.assertEqual(read_token_file(path),'selected-account-token')
            path.write_text('raw-account-token')
            self.assertEqual(read_token_file(path),'raw-account-token')
            for invalid in ['MCD_MCP_TOKEN=','NOT_A_TOKEN=value','']:
                path.write_text(invalid)
                with self.assertRaises(ValueError):read_token_file(path)

    def test_cli_selected_account_file_and_hidden_name(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'MCD_MCP_TOKEN':'wrong-account-token'}):
            path=Path(tmp)/'.env_example';path.write_text('MCD_MCP_TOKEN=chosen-account-token\n')
            with patch('mcd_life_kit.cli.MCPClient.list_tools',return_value=[]), \
                 patch('mcd_life_kit.cli.collect_orders',return_value=([],[])) as collect, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['identity-card','--env-file',str(path),'--html-only','--file-suffix','example','--output',tmp]),0)
            self.assertEqual(collect.call_args[0][0].token,'chosen-account-token')
            result=(Path(tmp)/'identity-card_example.html').read_text()
            self.assertIn('class="nickname" hidden',result)
            self.assertNotIn('麦门同学',result)

    def test_suffix_and_optional_names_in_both_artifacts(self):
        report=summarize([],2026);report['identity']=make_identity(report)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            annual,_=generate_report(report,out,'example',png=False,file_suffix='example')
            card,_=generate_visual(report,out,'example','identity-card',png=False,file_suffix='example')
            self.assertEqual(annual.name,'annual-report_example.html')
            self.assertEqual(card.name,'identity-card_example.html')
            self.assertIn('example',annual.read_text())
            self.assertIn('>example</p>',card.read_text())
            self.assertIn('class="nickname" hidden',render_visual(report,None,'identity-card'))
        for bad in ['../escape','a/b','a.b','a\\b']:
            with self.assertRaises(ValueError):artifact_stem('report',bad)


if __name__=='__main__':unittest.main()
