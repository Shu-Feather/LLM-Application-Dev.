import ast
import operator as op
import sqlite3
import requests

class CalculatorTool:
    ALLOWED_OPERATORS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg}
    def eval_expr(self, expr: str):
        try:
            node = ast.parse(expr, mode='eval').body
            return self._eval(node)
        except Exception as e:
            return f"Calc error: {e}"
    def _eval(self, node):
        if isinstance(node, ast.Num): return node.n
        if isinstance(node, ast.BinOp) and type(node.op) in self.ALLOWED_OPERATORS:
            return self.ALLOWED_OPERATORS[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.ALLOWED_OPERATORS:
            return self.ALLOWED_OPERATORS[type(node.op)](self._eval(node.operand))
        raise ValueError(f"Unsupported: {node}")

class DatabaseTool:
    def __init__(self, db_path: str = None):
        path = db_path or 'data.db'
        self.conn = sqlite3.connect(path)
    def execute(self, query: str):
        try:
            c = self.conn.cursor()
            c.execute(query)
            if query.strip().lower().startswith('select'):
                return c.fetchall()
            self.conn.commit()
            return "OK"
        except Exception as e:
            return f"DB error: {e}"

class APITool:
    def call(self, method: str, url: str, params: dict=None, headers: dict=None, data: dict=None):
        try:
            resp = requests.request(method, url, params=params, headers=headers, json=data, timeout=10)
            ct = resp.headers.get('Content-Type','')
            if 'application/json' in ct:
                return {'status': resp.status_code, 'data': resp.json()}
            return {'status': resp.status_code, 'text': resp.text}
        except Exception as e:
            return {'error': str(e)}

class PythonInterpreterTool:
    def execute(self, code: str):
        try:
            local = {}
            exec(code, {}, local)
            return local
        except Exception as e:
            return f"Exec error: {e}"