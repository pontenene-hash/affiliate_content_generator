import ast
import unittest
from pathlib import Path
from unittest.mock import Mock

class BatchRecovery(unittest.TestCase):
    def test_history_failure_stops_both_paths(self):
        tree=ast.parse(Path(__file__).with_name('auto_pipeline.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_batch')
        calls=[]
        for n in ast.walk(fn):
            if isinstance(n,ast.Try) and any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='record_saved_draft' for x in n.body):
                calls.append(n)
                self.assertTrue(any(isinstance(x,ast.Break) for h in n.handlers for x in h.body))
                self.assertTrue(any(isinstance(x,ast.Constant) and x.value=='wp_id' for h in n.handlers for x in ast.walk(h)))
        self.assertEqual(len(calls),2)
    def test_five_unique_topics(self):
        from article_history import next_topics
        items=[{'title':f'商品{i}','genre':'暮らし','product_url':f'https://example.com/{i}','affiliate_url':f'https://example.com/ad/{i}'} for i in range(3)]
        tasks=next_topics(items,[],5)
        self.assertEqual(len(tasks),5)
        self.assertEqual(len({t[1] for t in tasks}),5)
        history=[{'key':t[1]} for t in tasks]
        self.assertFalse({t[1] for t in tasks}&{t[1] for t in next_topics(items,history,5)})
