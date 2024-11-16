import re
from abc import ABC, abstractmethod
from enum import IntEnum, unique

from parserleaf import ParserLeaf


class ParserNode(ABC):
    @unique
    class ParserState(IntEnum):
        NONE = 0
        FUNCTION_REACHED = 1
        BODY_REACHED = 2
        CONTROLFLOW_REACHED = 3

    def __init__(self, file, scope) -> None:
        self._file = file
        self._scope = scope
        self._cf_start = {'if', 'else'}
        self._children = []
        self._analyzed = False

    def _analyze(self) -> None:
        if self._analyzed:
            return
        lines, controlflows = self._get_lines()
        statements = self._get_statements(lines)
        calls = self._get_calls(statements)
        self._create_children(calls, controlflows)
        self._analyzed = True

    @abstractmethod
    def _get_lines(self) -> tuple[list, list]:
        pass

    def _get_statements(self, lines) -> list:
        stmts = ' '.join(lines)  # Join lines into one strings
        stmts = re.sub(r'\s+', ' ', stmts)  # Remove extra spaces
        stmts = stmts.split(';')  # Split by semicolon
        # Remove empty strings and leading/trailing whitespaces
        stmts = [stmt.strip() for stmt in stmts if stmt]
        return stmts

    def _get_calls(self, stmts) -> list:
        def predicate(stmt) -> bool:
            return stmt.endswith(')')

        calls = list(filter(predicate, stmts))
        return calls

    def _create_children(self, calls, controlflows) -> None:
        for call in calls:
            if leaf := ParserLeaf.create(call, self._scope):
                self._children.append(leaf)
            elif match := re.match(r'Graph\s+(\w+)\s*=\s*(\w+)\(', call):
                self._children.append(
                    FunctionNode(match.group(2), self._file, match.group(1))
                )
            elif match := re.search(r'\b([a-zA-Z_]\w*)\s*\(', call):
                self._children.append(
                    FunctionNode(match.group(1), self._file, self._scope)
                )
            else:
                raise ValueError(
                    f'"{call}" is not a function call according to regex!'
                )
        for cf in controlflows:
            self._children.append(
                ControlflowNode.create(cf, self._file, self._scope)
            )

    def translate(self) -> list:
        # Lazy evaluation
        self._analyze()
        plantuml = []
        for child in self._children:
            plantuml += child.translate()
        return plantuml


class FunctionNode(ParserNode):
    def __init__(self, name, file, scope) -> None:
        super().__init__(file, scope)
        self._name = name

    def _get_lines(self) -> tuple[list, list]:
        with open(self._file, 'r', encoding='utf8') as file:
            lines, controlflows, curr_cf = [], [], []
            state = self.ParserState.NONE
            open_curly_braces, open_cf_curly_braces = 0, 0

            for line in file:
                line = re.sub(r'//.*', '', line)  # Remove comments
                line = line.strip()
                if not line:
                    continue
                open_curly_braces += line.count('{') - line.count('}')

                match state:
                    case self.ParserState.NONE:
                        if f'{self._name}(' in line:
                            if open_curly_braces == 0:
                                state = self.ParserState.FUNCTION_REACHED
                            elif '{' in line:
                                state = self.ParserState.BODY_REACHED
                    case self.ParserState.FUNCTION_REACHED:
                        if open_curly_braces > 0:
                            state = self.ParserState.BODY_REACHED
                    case self.ParserState.BODY_REACHED:
                        if open_curly_braces == 0:  # Function body end
                            break
                        if any(
                            line.startswith(keyword)
                            for keyword in self._cf_start
                        ):
                            state = self.ParserState.CONTROLFLOW_REACHED
                            curr_cf.append(line)
                            open_cf_curly_braces += line.count(
                                '{'
                            ) - line.count('}')
                            continue
                        lines.append(line)
                    case self.ParserState.CONTROLFLOW_REACHED:
                        open_cf_curly_braces += line.count('{') - line.count(
                            '}'
                        )
                        curr_cf.append(line)
                        if open_cf_curly_braces == 0:
                            controlflows.append(curr_cf.copy())
                            curr_cf.clear()
                            state = self.ParserState.BODY_REACHED
            return lines, controlflows

    def translate(self) -> list:
        body = super().translate()
        if self._scope and body:  # Internal subgraph
            gname = self._name.removeprefix('Create')
            first = f'cloud "{gname}" as {self._scope} {{'
            last = '}'
            return [first] + body + [last]
        return body


class ControlflowNode(ParserNode):
    count = 0

    def __init__(self, cf_block, file, scope) -> None:
        super().__init__(file, scope)
        self._block = cf_block

    def _get_lines(self) -> tuple[list, list]:
        lines, controlflows, curr_cf = [], [], []
        state = self.ParserState.NONE
        open_curly_braces, open_cf_curly_braces = 0, 0

        for line in self._block:
            # Comments and empty lines already removed in FunctionNode
            open_curly_braces += line.count('{') - line.count('}')

            match state:
                case self.ParserState.NONE:
                    if '{' in line:
                        state = self.ParserState.BODY_REACHED
                case self.ParserState.BODY_REACHED:
                    if open_curly_braces == 0:  # controlflow body end
                        break
                    if any(
                        line.startswith(keyword) for keyword in self._cf_start
                    ):
                        state = self.ParserState.CONTROLFLOW_REACHED
                        curr_cf.append(line)
                        open_cf_curly_braces += line.count('{') - line.count(
                            '}'
                        )
                        continue
                    lines.append(line)
                case self.ParserState.CONTROLFLOW_REACHED:
                    open_cf_curly_braces += line.count('{') - line.count('}')
                    curr_cf.append(line)
                    if open_cf_curly_braces == 0:
                        controlflows.append(curr_cf.copy())
                        curr_cf.clear()
                        state = self.ParserState.BODY_REACHED
        return lines, controlflows

    def _get_condition(self) -> str:
        stmt = self._block[0]
        match = re.search(r'\bif\s*\((.+)\)', stmt)
        condition = match.group(1) if match else ''
        return condition

    @classmethod
    def create(cls, block, file, scope) -> 'ControlflowNode':
        # Pattern matching
        match block[0].split():
            case ['if', *_]:
                return IfNode(block, file, scope)
            case ['else', 'if', *_]:
                return ElseIfNode(block, file, scope)
            case ['else', *_]:
                return ElseNode(block, file, scope)
            case _:
                raise ValueError(f'No matching controlflow for "{block[0]}"')


class IfNode(ControlflowNode):
    def translate(self) -> list:
        body = super().translate()
        condition = super()._get_condition()
        first = f'rectangle "if {condition}" as cf{ControlflowNode.count} {{'
        last = '}'
        ControlflowNode.count += 1
        return [first] + body + [last]


class ElseIfNode(ControlflowNode):
    def translate(self) -> list:
        body = super().translate()
        condition = super()._get_condition()
        first = (
            f'rectangle "else if {condition}" as cf{ControlflowNode.count} {{'
        )
        last = '}'
        ControlflowNode.count += 1
        return [first] + body + [last]


class ElseNode(ControlflowNode):
    def translate(self) -> list:
        body = super().translate()
        first = f'rectangle "else" as cf{ControlflowNode.count} {{'
        last = '}'
        ControlflowNode.count += 1
        return [first] + body + [last]
