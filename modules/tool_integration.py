import ast
import operator as op
import re
import sqlite3
import requests
import math

class CalculatorTool:
    ALLOWED_OPERATORS = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.Mod: op.mod,
        ast.USub: op.neg,
        ast.FloorDiv: op.floordiv
    }
    
    # 支持的函数
    FUNCTIONS = {
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log10,
        'ln': math.log,
        'abs': abs,
        'fact': math.factorial,
        'exp': math.exp
    }
    
    CONSTANTS = {
        'pi': math.pi,
        'e': math.e
    }

    def eval_expr(self, expr: str):
        try:
            # 预处理表达式：替换 ^ 为 **，处理函数和常量
            expr = self.preprocess_expression(expr)
            
            # 解析表达式
            node = ast.parse(expr, mode='eval').body
            return self._eval(node)
        except Exception as e:
            return f"计算错误: {str(e)}"

    def preprocess_expression(self, expr: str) -> str:
        """预处理数学表达式"""
        # 替换 ^ 为 **（幂运算）
        expr = expr.replace('^', '**')
        
        # 替换函数名中的特殊字符
        expr = re.sub(r'(\b[a-zA-Z_]+)\s*\(', r'\1(', expr)
        
        return expr

    def _eval(self, node):
        """递归计算表达式"""
        # 数字节点
        if isinstance(node, ast.Num):
            return node.n
            
        # 常量节点
        if isinstance(node, ast.Name) and node.id in self.CONSTANTS:
            return self.CONSTANTS[node.id]
            
        # 二元运算符
        if isinstance(node, ast.BinOp) and type(node.op) in self.ALLOWED_OPERATORS:
            left_val = self._eval(node.left)
            right_val = self._eval(node.right)
            return self.ALLOWED_OPERATORS[type(node.op)](left_val, right_val)
            
        # 一元运算符
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.ALLOWED_OPERATORS:
            operand_val = self._eval(node.operand)
            return self.ALLOWED_OPERATORS[type(node.op)](operand_val)
            
        # 函数调用
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.FUNCTIONS:
                args = [self._eval(arg) for arg in node.args]
                return self.FUNCTIONS[func_name](*args)
            else:
                raise ValueError(f"不支持的函数: {func_name}")
                
        # 比较运算符（添加简单比较功能）
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = self._eval(right_node)
                if isinstance(op, ast.Eq):
                    result = left == right
                elif isinstance(op, ast.NotEq):
                    result = left != right
                elif isinstance(op, ast.Lt):
                    result = left < right
                elif isinstance(op, ast.LtE):
                    result = left <= right
                elif isinstance(op, ast.Gt):
                    result = left > right
                elif isinstance(op, ast.GtE):
                    result = left >= right
                else:
                    raise ValueError(f"不支持的比较运算符: {type(op).__name__}")
                left = right  # 用于链式比较
            return result
            
        # 不支持的类型
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")

    def calculate(self, expression: str):
        """用户友好的计算接口"""
        try:
            # 移除空格和特殊字符
            expression = expression.replace(' ', '')
            
            # 检查是否为简单计算
            if re.match(r'^[\d+\-*/^().]+$', expression):
                return self.eval_expr(expression)
                
            # 尝试解析为数学表达式
            return self.eval_expr(expression)
        except Exception as e:
            return f"计算错误: {str(e)}"

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