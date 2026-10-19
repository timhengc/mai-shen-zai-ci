import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcd_life_kit.cli import main
from mcd_life_kit.mcp_client import MCPError
from mcd_life_kit.onboarding import generate_setup, read_session_token
from mcd_life_kit.annual_report import load_env


class OnboardingTests(unittest.TestCase):
    def test_first_use_precedes_menu_without_private_query(self):
        with patch.dict('os.environ', {}, clear=True), patch('mcd_life_kit.cli.load_env'), \
             patch('mcd_life_kit.cli.show_setup') as setup, patch('mcd_life_kit.cli.collect_orders') as collect:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([]), 0)
            setup.assert_called_once()
            collect.assert_not_called()
            self.assertNotIn('请选择要制作', output.getvalue())

    def test_configured_user_skips_repeat_login(self):
        with patch.dict('os.environ', {'MCD_MCP_TOKEN':'configured-test-token'}, clear=True), \
             patch('mcd_life_kit.cli.load_env'), patch('mcd_life_kit.cli.show_setup') as setup:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([]), 0)
            setup.assert_not_called()
            self.assertIn('请选择要制作', output.getvalue())
            self.assertNotIn('configured-test-token', output.getvalue())

    def test_visual_command_without_token_shows_guide_and_stops(self):
        with patch.dict('os.environ', {}, clear=True), patch('mcd_life_kit.cli.load_env'), \
             patch('mcd_life_kit.cli.show_setup') as setup, patch('mcd_life_kit.cli.collect_orders') as collect:
            self.assertEqual(main(['avatar','--html-only']), 2)
            setup.assert_called_once()
            collect.assert_not_called()

    def test_offline_guide_embeds_both_images_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'MCD_MCP_TOKEN':'never-embed-this-token'}):
            result = generate_setup(Path(tmp)).read_text()
            self.assertIn('https://open.mcd.cn/mcp', result)
            self.assertEqual(result.count('src="data:image/png;base64,'), 2)
            self.assertNotIn('__QR_IMAGE__', result)
            self.assertNotIn('__GUIDE_IMAGE__', result)
            self.assertNotIn('never-embed-this-token', result)

    def test_session_token_input_and_multiline_rejection(self):
        with patch('sys.stdin', io.StringIO('session-test-token\n')):
            self.assertEqual(read_session_token(), 'session-test-token')
        for invalid in ['', 'token with spaces', 'token\nOTHER=value', 'token\x00']:
            with self.subTest(invalid=invalid), patch('sys.stdin', io.StringIO(invalid)):
                with self.assertRaises(ValueError):
                    read_session_token()
        with patch('sys.stdin.isatty', return_value=True), \
             patch('mcd_life_kit.onboarding.getpass.getpass', return_value='hidden-test-token') as hidden:
            self.assertEqual(read_session_token(), 'hidden-test-token')
            hidden.assert_called_once()

    def test_chat_token_overrides_configuration_and_is_not_saved(self):
        token = 'session-only-test-token'
        seen = []
        def collect(client, *args, **kwargs):
            seen.append(client.token)
            return [], []
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict('os.environ', {'MCD_MCP_TOKEN':'other-configured-token'}, clear=True), \
             patch('mcd_life_kit.cli.load_env'), patch('sys.stdin', io.StringIO(token)), \
             patch('mcd_life_kit.cli.MCPClient.list_tools', return_value=[]), \
             patch('mcd_life_kit.cli.collect_orders', side_effect=collect), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['avatar','--token-stdin','--html-only','--output',tmp]), 0)
            self.assertEqual(seen, [token])
            self.assertNotIn(token, output.getvalue())
            self.assertFalse((Path(tmp)/'.env').exists())
            self.assertTrue(all(token.encode() not in p.read_bytes() for p in Path(tmp).iterdir()))

    def test_upstream_error_cannot_echo_session_token(self):
        token = 'must-hide-test-token'
        with patch('mcd_life_kit.cli.load_env'), patch('sys.stdin', io.StringIO(token)), \
             patch('mcd_life_kit.cli.MCPClient.list_tools', return_value=[]), \
             patch('mcd_life_kit.cli.collect_orders', side_effect=MCPError('failed: '+token)), \
             contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(main(['avatar','--token-stdin','--html-only']), 1)
            self.assertNotIn(token, output.getvalue())
            self.assertIn('Token 已隐藏', output.getvalue())

    def test_downloaded_config_loads_without_renaming_and_respects_priority(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {}, clear=True):
            root = Path(tmp)
            (root/'mcd-token.env').write_text('MCD_MCP_TOKEN=downloaded-test-token\n')
            with patch('mcd_life_kit.annual_report.ROOT', root):
                load_env(root/'.env')
                self.assertEqual(os.environ['MCD_MCP_TOKEN'], 'downloaded-test-token')
                (root/'.env').write_text('MCD_MCP_TOKEN=preferred-dotenv-token\n')
                os.environ.pop('MCD_MCP_TOKEN')
                load_env(root/'.env')
                self.assertEqual(os.environ['MCD_MCP_TOKEN'], 'preferred-dotenv-token')
                os.environ['MCD_MCP_TOKEN']='environment-test-token'
                load_env(root/'.env')
                self.assertEqual(os.environ['MCD_MCP_TOKEN'], 'environment-test-token')


if __name__ == '__main__':
    unittest.main()
