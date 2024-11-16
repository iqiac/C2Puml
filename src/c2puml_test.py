from unittest.mock import MagicMock, mock_open, patch

from parserleaf import ExternalGraphLeaf, UtilityLeaf
from parsernode import ControlflowNode, ElseIfNode, ElseNode, FunctionNode, IfNode


class MockFile:
    def __init__(self) -> None:
        self.utilityfunctions = ""
        self.controlflow = ""
        self.externalSubgraph = ""
        self.internalSubgraphDefinition = ""
        self.internalSubgraphCall = ""

    def with_utility_functions(self) -> "MockFile":
        self.utilityfunctions = '''
        Utility_LinkDirectedHard(start, util1); // start --> util1
        Utility_LinkDirectedSoft(util1, util2); // util1 ..> util2
        Utility_LinkUndirected(util2, end); // util2 -- end
        '''
        return self

    def with_control_flow(self) -> "MockFile":
        self.controlflow = '''
        Utility_LinkUndirected(start, cf);

        if (condition1) {
          Utility_LinkUndirected(cf, cf1);
        }
        else if (condition2 || condition3) {
          Utility_LinkUndirected(cf, cf2);
        }
        else {
          Utility_LinkUndirected(cf, cf3);
        }

        Utility_LinkUndirected(cf, end);
        '''
        return self

    def with_external_subgraph(self) -> "MockFile":
        self.externalSubgraph = '''
        Graph extGraph1 = ExternalGraph_Create(parameters);
        Graph extGraph2 = ExternalGraph_Create(parameters);

        Utility_LinkDirectedHard(start, extGraph1.start);
        Utility_LinkDirectedHard(extGraph1.end, extDelay);

        Utility_LinkDirectedHard(extDelay, extGraph2.start);
        Utility_LinkDirectedHard(extGraph2.end, end);
        '''
        return self

    def with_internal_subgraph(self) -> "MockFile":
        self.internalSubgraphDefinition = '''
        static Graph CreateInternalSubgraph(int arg1, int arg2, int arg3) {
          Node* start = Utility_CreateStart();
          Node* end = Utility_CreateEnd();
          Node* node1 = Utility_CreateTask(arg1);
          Node* node2 = Utility_CreateTask(arg2);
          Node* node3 = Utility_CreateTask(arg3);

          Utility_LinkDirectedHard(start, node1);
          Utility_LinkDirectedHard(node1, node2);
          Utility_LinkDirectedHard(node2, node3);
          Utility_LinkDirectedHard(node3, end);

          Graph mockSubgraph = {{.start = start, .end = end}};
          return mockSubgraph;
        }
        '''
        self.internalSubgraphCall = '''
        Graph intGraph1 = CreateInternalSubgraph(arg1, arg2, arg3);
        Graph intGraph2 = CreateInternalSubgraph(arg1, arg2, arg3);

        Utility_LinkDirectedSoft(start, intGraph1.start);
        Utility_LinkDirectedSoft(intGraph1.end, node);

        Utility_LinkDirectedSoft(node, intGraph2.start);
        Utility_LinkDirectedSoft(intGraph2.end, end);
        '''
        return self

    def build(self) -> MagicMock:
        content = f'''
        #include "MockGraph.h"
        #include "Configuration.h"
        #include "ExternalGraph.h"
        #include "Utility.h"

        {self.internalSubgraphDefinition}

        static Graph CreateMockGraph(int arg1, int arg2, int arg3) {{
          // Define some nodes
          Node* start = Utility_CreateStart();
          Node* end = Utility_CreateEnd();

          Node* task = Utility_CreateTask(0);

          {self.utilityfunctions}

          {self.controlflow}

          {self.externalSubgraph}

          {self.internalSubgraphCall}

          g_TGraph mockGraph = {{ .start = start, .end = end }};
          return mockGraph;
        }}

        Graph MockGraph_Create(Parameters params) {{
          int arg1 = params.param1;
          int arg2 = params.param2;
          int arg3 = params.param3;
          return CreateMockGraph(arg1, arg2, arg3);
        }}
        '''
        return mock_open(read_data=content)


class TestFileBase:
    @classmethod
    def setup_class(cls) -> None:
        cls.filepath = "MockGraph.c"
        cls.mockFile = MockFile().build()

    def test_FunctionNode_GetLinesSimple(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("MockGraph_Create", self.filepath, "")

            lines, controlflows = node._get_lines()

            expected = [
                "int arg1 = params.param1;",
                "int arg2 = params.param2;",
                "int arg3 = params.param3;",
                "return CreateMockGraph(arg1, arg2, arg3);",
            ]
            assert lines == expected
            assert not controlflows

    def test_FunctionNode_GetStatementsSimple(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("MockGraph_Create", self.filepath, "")
            lines, _ = node._get_lines()

            stmts = node._get_statements(lines)

            expected = [
                "int arg1 = params.param1",
                "int arg2 = params.param2",
                "int arg3 = params.param3",
                "return CreateMockGraph(arg1, arg2, arg3)",
            ]
            assert stmts == expected

    def test_FunctionNode_GetCallsSimple(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("MockGraph_Create", self.filepath, "")
            lines, _ = node._get_lines()
            stmts = node._get_statements(lines)

            calls = node._get_calls(stmts)

            expected = ["return CreateMockGraph(arg1, arg2, arg3)"]
            assert calls == expected

    def test_FunctionNode_GetLinesComplex(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("CreateMockGraph", self.filepath, "")

            lines, controlflows = node._get_lines()

            expected = [
                "Node* start = Utility_CreateStart();",
                "Node* end = Utility_CreateEnd();",
                "Node* task = Utility_CreateTask(0);",
                "g_TGraph mockGraph = { .start = start, .end = end };",
                "return mockGraph;",
            ]
            assert lines == expected
            assert not controlflows

    def test_FunctionNode_GetStatementsComplex(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("CreateMockGraph", self.filepath, "")
            lines, _ = node._get_lines()

            stmts = node._get_statements(lines)

            expected = [
                "Node* start = Utility_CreateStart()",
                "Node* end = Utility_CreateEnd()",
                "Node* task = Utility_CreateTask(0)",
                "g_TGraph mockGraph = { .start = start, .end = end }",
                "return mockGraph",
            ]
            assert stmts == expected

    def test_FunctionNode_GetCallsComplex(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("CreateMockGraph", self.filepath, "")
            lines, _ = node._get_lines()
            stmts = node._get_statements(lines)

            calls = node._get_calls(stmts)

            expected = [
                "Node* start = Utility_CreateStart()",
                "Node* end = Utility_CreateEnd()",
                "Node* task = Utility_CreateTask(0)",
            ]
            assert calls == expected

    def test_FunctionNode_CreateChildren(self) -> None:
        with patch("builtins.open", self.mockFile):
            node = FunctionNode("CreateMockGraph", self.filepath, "")
            lines, controlflows = node._get_lines()
            stmts = node._get_statements(lines)
            calls = node._get_calls(stmts)

            node._create_children(calls, controlflows)

            children = node._children
            assert len(children) == 3
            assert all(isinstance(c, FunctionNode) for c in children)


class TestFileWithUtilityFunctions:
    @classmethod
    def setup_class(cls) -> None:
        filepath = "MockGraph.c"
        mockFile = MockFile().with_utility_functions().build()
        with patch("builtins.open", mockFile):
            cls.node = FunctionNode("CreateMockGraph", filepath, "")
            cls.lines, cls.controlflows = cls.node._get_lines()

    def test_FunctionNode_GetLines(self) -> None:
        expected_subset = [
            "Utility_LinkDirectedHard(start, util1);",
            "Utility_LinkDirectedSoft(util1, util2);",
            "Utility_LinkUndirected(util2, end);",
        ]
        assert set(expected_subset).issubset(set(self.lines))
        assert not self.controlflows

    def test_FunctionNode_GetStatements(self) -> None:
        stmts = self.node._get_statements(self.lines)

        expected_subset = [
            "Utility_LinkDirectedHard(start, util1)",
            "Utility_LinkDirectedSoft(util1, util2)",
            "Utility_LinkUndirected(util2, end)",
        ]
        assert set(expected_subset).issubset(set(stmts))
        assert len(stmts) == 8

    def test_FunctionNode_GetCalls(self) -> None:
        stmts = self.node._get_statements(self.lines)

        calls = self.node._get_calls(stmts)

        expected_subset = [
            "Utility_LinkDirectedHard(start, util1)",
            "Utility_LinkDirectedSoft(util1, util2)",
            "Utility_LinkUndirected(util2, end)",
        ]
        assert set(expected_subset).issubset(set(calls))
        assert len(calls) == 6

    def test_FunctionNode_CreateChildren(self) -> None:
        stmts = self.node._get_statements(self.lines)
        calls = self.node._get_calls(stmts)

        self.node._create_children(calls, self.controlflows)

        children = self.node._children
        assert len(children) == 6
        assert sum(isinstance(c, UtilityLeaf) for c in children) == 3

    def test_UtilityLeaf_TranslateDirectHard(self) -> None:
        leaf = UtilityLeaf("Utility_LinkDirectedHard(parent, child)", "")

        translated = leaf.translate()

        assert translated

    def test_UtilityLeaf_TranslateDirectSoft(self) -> None:
        leaf = UtilityLeaf("Utility_LinkDirectedSoft(parent, child)", "")

        translated = leaf.translate()

        assert translated

    def test_UtilityLeaf_TranslateUndirected(self) -> None:
        leaf = UtilityLeaf("Utility_LinkUndirected(parent, child)", "")

        translated = leaf.translate()

        assert translated


class TestFileWithControlFlow:
    @classmethod
    def setup_class(cls) -> None:
        filepath = "MockGraph.c"
        mockFile = MockFile().with_control_flow().build()
        with patch("builtins.open", mockFile):
            cls.node = FunctionNode("CreateMockGraph", filepath, "")
            cls.lines, cls.controlflows = cls.node._get_lines()

    def test_FunctionNode_GetLines(self) -> None:
        expected_cf_elements = [
            ["if (condition1) {", "Utility_LinkUndirected(cf, cf1);", "}"],
            [
                "else if (condition2 || condition3) {",
                "Utility_LinkUndirected(cf, cf2);",
                "}",
            ],
            ["else {", "Utility_LinkUndirected(cf, cf3);", "}"],
        ]
        expected_lines = [
            "Utility_LinkUndirected(start, cf);",
            "Utility_LinkUndirected(cf, end);",
        ]
        assert self.controlflows == expected_cf_elements
        assert set(expected_lines).issubset(set(self.lines))
        assert len(self.controlflows) == 3
        assert len(self.lines) == 7

    def test_FunctionNode_CreateChildren(self) -> None:
        stmts = self.node._get_statements(self.lines)
        calls = self.node._get_calls(stmts)

        self.node._create_children(calls, self.controlflows)

        children = self.node._children
        assert len(children) == 8
        assert sum(isinstance(c, ControlflowNode) for c in children) == 3


class TestControlflowNodes:
    @classmethod
    def setup_class(cls) -> None:
        def extract(l, t) -> list:
            return [x for x in l if isinstance(x, t)]

        filepath = "MockGraph.c"
        mockFile = MockFile().with_control_flow().build()
        with patch("builtins.open", mockFile):
            node = FunctionNode("CreateMockGraph", filepath, "")
            node._analyze()
            children = node._children
            cls.if_node = extract(children, IfNode)[0]
            cls.elseif_node = extract(children, ElseIfNode)[0]
            cls.else_node = extract(children, ElseNode)[0]

    def test_IfNode_GetLines(self) -> None:
        if_lines, if_controlflows = self.if_node._get_lines()

        if_expected = ["Utility_LinkUndirected(cf, cf1);"]
        assert if_lines == if_expected
        assert if_controlflows == []

    def test_ElseIfNode_GetLines(self) -> None:
        elseif_lines, elseif_controlflows = self.elseif_node._get_lines()

        elseif_expected = ["Utility_LinkUndirected(cf, cf2);"]
        assert elseif_lines == elseif_expected
        assert elseif_controlflows == []

    def test_ElseNode_GetLines(self) -> None:
        else_lines, else_controlflows = self.else_node._get_lines()

        else_expected = ["Utility_LinkUndirected(cf, cf3);"]
        assert else_lines == else_expected
        assert else_controlflows == []

    def test_IfNode_GetCondition(self) -> None:
        condition = self.if_node._get_condition()

        assert condition == "condition1"

    def test_ElseIfNode_GetCondition(self) -> None:
        condition = self.elseif_node._get_condition()

        assert condition == "condition2 || condition3"

    def test_ElseNode_GetCondition(self) -> None:
        condition = self.else_node._get_condition()

        assert condition == ""


class TestFileWithExternalGraph:
    @classmethod
    def setup_class(cls) -> None:
        filepath = "MockGraph.c"
        mockFile = MockFile().with_external_subgraph().build()
        with patch("builtins.open", mockFile):
            cls.node = FunctionNode("CreateMockGraph", filepath, "")
            cls.lines, cls.controlflows = cls.node._get_lines()

    def test_FunctionNode_GetLines(self) -> None:
        expected_subset = [
            "Graph extGraph1 = ExternalGraph_Create(parameters);",
            "Graph extGraph2 = ExternalGraph_Create(parameters);",
            "Utility_LinkDirectedHard(start, extGraph1.start);",
            "Utility_LinkDirectedHard(extGraph1.end, extDelay);",
            "Utility_LinkDirectedHard(extDelay, extGraph2.start);",
            "Utility_LinkDirectedHard(extGraph2.end, end);",
        ]
        assert set(expected_subset).issubset(set(self.lines))
        assert not self.controlflows

    def test_FunctionNode_GetStatements(self) -> None:
        stmts = self.node._get_statements(self.lines)

        expected_subset = [
            "Graph extGraph1 = ExternalGraph_Create(parameters)",
            "Graph extGraph2 = ExternalGraph_Create(parameters)",
        ]
        assert set(expected_subset).issubset(set(stmts))

    def test_FunctionNode_GetCalls(self) -> None:
        stmts = self.node._get_statements(self.lines)

        calls = self.node._get_calls(stmts)

        expected_subset = [
            "Graph extGraph1 = ExternalGraph_Create(parameters)",
            "Graph extGraph2 = ExternalGraph_Create(parameters)",
        ]
        assert set(expected_subset).issubset(set(calls))

    def test_FunctionNode_CreateChildren(self) -> None:
        stmts = self.node._get_statements(self.lines)
        calls = self.node._get_calls(stmts)

        self.node._create_children(calls, self.controlflows)

        children = self.node._children
        assert len(children) == 9
        assert sum(isinstance(c, ExternalGraphLeaf) for c in children) == 2

    def test_ExternalFunctionLeaf_Translate1(self) -> None:
        leaf = ExternalGraphLeaf(
            "Graph extGraph = ExternalGraph_Create(parameters)", ""
        )

        translated = leaf.translate()

        assert translated


class TestFileWithInternalSubgraph:
    @classmethod
    def setup_class(cls) -> None:
        def predicate(c) -> bool:
            return (
                isinstance(c, FunctionNode)
                and c._name == "CreateInternalSubgraph"
            )

        filepath = "MockGraph.c"
        mockFile = MockFile().with_internal_subgraph().build()
        with patch("builtins.open", mockFile):
            node = FunctionNode("CreateMockGraph", filepath, "")
            node._analyze()
            cls.fchildren = [c for c in node._children if predicate(c)]
            fchild = cls.fchildren[0]
            cls.lines, cls.controlflows = fchild._get_lines()

    def test_FunctionNode_CreateChildren(self) -> None:
        assert len(self.fchildren) == 2

    def test_FunctionNodeChild_GetLines(self):
        expected = [
            "Node* start = Utility_CreateStart();",
            "Node* end = Utility_CreateEnd();",
            "Node* node1 = Utility_CreateTask(arg1);",
            "Node* node2 = Utility_CreateTask(arg2);",
            "Node* node3 = Utility_CreateTask(arg3);",
            "Utility_LinkDirectedHard(start, node1);",
            "Utility_LinkDirectedHard(node1, node2);",
            "Utility_LinkDirectedHard(node2, node3);",
            "Utility_LinkDirectedHard(node3, end);",
            "Graph mockSubgraph = {{.start = start, .end = end}};",
            "return mockSubgraph;",
        ]
        assert self.lines == expected
        assert self.controlflows == []
