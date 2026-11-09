"""Verify transport selection without scraping, email or network side effects."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
class RolloutTests(unittest.TestCase):
 def test_only_legacy_mode_posts_the_original_webhook_payload(self):
  tree=ast.parse((ROOT/'scripts/tanaka.py').read_text(encoding='utf-8'))
  branch=next(n for n in tree.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='LINEWORKS_DELIVERY_MODE' and isinstance(n.test.ops[0],ast.Eq))
  code=compile(ast.Module(body=[branch],type_ignores=[]),'<delivery-mode>','exec')
  for mode,count in [('gas-card',0),('webhook',1)]:
   with self.subTest(mode=mode):
    requests=Mock();requests.post.return_value.status_code=200
    exec(code,{'LINEWORKS_DELIVERY_MODE':mode,'requests':requests,'LINEWORKS_WEBHOOK_URL':'synthetic-url','lineworks_message':'synthetic-message'})
    self.assertEqual(requests.post.call_count,count)
    if count:self.assertEqual(requests.post.call_args.kwargs['json'],{'body':{'text':'synthetic-message'}})
 def test_workflow_selects_card_without_changing_mail_or_publication_guard(self):
  source=(ROOT/'.github/workflows/tanaka_notify.yml').read_text(encoding='utf-8')
  self.assertIn('LINEWORKS_DELIVERY_MODE: gas-card',source)
  self.assertIn('SMTP_PASSWORD:         ${{ secrets.BREVO_SMTP_KEY }}',source)
  self.assertIn('git add data/tanaka_notify_log.json',source)
  self.assertIn("if: steps.notify_guard.outputs.already_sent != 'true'",source)
if __name__=='__main__':unittest.main()
