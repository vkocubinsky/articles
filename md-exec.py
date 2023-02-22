#!/usr/bin/env python3

import io
import pathlib
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    TEXT = auto()
    PYTHON_BLOCK = auto()  # ```python
    OUTPUT_BLOCK = auto()  # ```output
    BLOCK = auto()  # ```


@dataclass
class Token:
    type: TokenType
    text: str


class Tokenizer:
    def __init__(self):
        self.tokens = []
        self.lines = []

    def flush(self):
        if self.lines:
            self.tokens.append(Token(TokenType.TEXT, "\n".join(self.lines)))
            self.lines = []

    def parse(self, text: str):
        # TODO: use regex for more precise match
        for line in text.splitlines():
            if line.startswith("```python"):
                self.flush()
                self.tokens.append(Token(TokenType.PYTHON_BLOCK, line))
            elif line.startswith("```output"):
                self.flush()
                self.tokens.append(Token(TokenType.OUTPUT_BLOCK, line))
            elif line.startswith("```"):
                self.flush()
                self.tokens.append(Token(TokenType.BLOCK, line))
            else:
                self.lines.append(line)
        self.flush()
        return self.tokens


@dataclass
class PythonBlock:
    begin_code_token: Token
    code_token: Token
    end_code_token: Token

    @property
    def text(self):
        return f"{self.begin_code_token.text}\n{self.code_token.text}\n{self.end_code_token.text}\n"


@dataclass
class OutputBlock:
    begin_output_token: Token
    output_token: Token
    end_output_token: Token

    @property
    def text(self):
        return f"{self.begin_output_token.text}\n{self.output_token.text}\n{self.end_output_token.text}\n"


@dataclass
class TextBlock:
    text_token: Token

    @property
    def text(self):
        return f"{self.text_token.text}\n"


class Parser:
    def __init__(self):
        self.blocks = []

    def expected_token(
        self, expected_token_type, on_index: int, tokens: list[Token]
    ) -> Token:
        if on_index >= len(tokens):
            raise ValueError(f"Bad index {on_index=}")
        token = tokens[on_index]
        if expected_token_type != token.type:
            raise ValueError(f"Expected {expected_token_type=}, but {token.type=}")
        return token

    def parse(self, text):
        tokens = Tokenizer().parse(text)
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token.type == TokenType.PYTHON_BLOCK:
                code_token = self.expected_token(TokenType.TEXT, index + 1, tokens)
                end_code_token = self.expected_token(TokenType.BLOCK, index + 2, tokens)
                self.blocks.append(PythonBlock(token, code_token, end_code_token))
                index += 3
            elif token.type == TokenType.OUTPUT_BLOCK:
                output_token = self.expected_token(TokenType.TEXT, index + 1, tokens)
                end_output_token = self.expected_token(
                    TokenType.BLOCK, index + 2, tokens
                )
                self.blocks.append(OutputBlock(token, output_token, end_output_token))
                index += 3
            else:
                self.blocks.append(TextBlock(token))
                index += 1
        return self.blocks


class CodeExecutor:
    def __init__(self):
        self.globals = {}

    def execute(self, code: str) -> str:
        with redirect_stdout(io.StringIO()) as f:
            with redirect_stderr(f):
                try:
                    compiled = compile(code, "", "exec")
                    exec(compiled, self.globals)
                except:
                    traceback.print_exc()
                return f.getvalue()


if __name__ == "__main__":
    text = pathlib.Path("partition-aggregation.md").read_text()
    code_executor = CodeExecutor()
    for block in Parser().parse(text):
        if isinstance(block, PythonBlock):
            print(block.text, end="")
            output = code_executor.execute(block.code_token.text)
            if output:
                print("```output")
                print(output, end="")
                print("```")
        elif isinstance(block, OutputBlock):
            pass
        else:
            print(block.text, end="")
