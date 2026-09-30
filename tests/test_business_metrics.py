import unittest
from prometheus_client.parser import text_string_to_metric_families
from Back.modules.chat.metrics import render_business_metrics


class BusinessMetricsTests(unittest.TestCase):
    def test_current_reactions_and_topics(self):
        text = render_business_metrics([(1, 7), (-1, 2), (0, 3)], [('ecp_cryptopro', 5)]).decode()
        samples = { (s.name, tuple(sorted(s.labels.items()))): s.value
            for family in text_string_to_metric_families(text) for s in family.samples }
        self.assertEqual(samples[('alpharag_bot_reactions', (('reaction','like'),))], 7)
        self.assertEqual(samples[('alpharag_bot_reactions', (('reaction','dislike'),))], 2)
        self.assertEqual(samples[('alpharag_questions_total', (('topic','ecp_cryptopro'),))], 5)
        self.assertIn('# TYPE alpharag_bot_reactions gauge', text)
        empty = render_business_metrics([], []).decode()
        self.assertIn('alpharag_bot_reactions{reaction="dislike"} 0.0', empty)
