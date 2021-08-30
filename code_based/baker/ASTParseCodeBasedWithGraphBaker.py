#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2020/2/16
------------------------------------------
@Modify: 2020/2/16
------------------------------------------
@Description: 
"""
from discussion.api_recognition.code_based.baker.ASTParseBasedWithGraphBaker import ASTParseBasedWithGraphBaker
from discussion.api_recognition.code_based.baker.CodeBasedWithGraphBaker import CodeBasedWithGraphBaker
from discussion.api_recognition.code_based.baker.base import BakerBaseClass


class ASTParseCodeBasedWithGraphBaker(BakerBaseClass):
    """
    baker based on AST parse + code recognize with graph
    """
    def __init__(self, graph, graph_client=None):
        super().__init__(graph=graph, graph_client=graph_client)
        self.code_based_baker = CodeBasedWithGraphBaker(graph=self.api_graph)
        self.ast_parse_based_baker = ASTParseBasedWithGraphBaker(graph=self.api_graph)

    def baker(self, code):
        api_qualified_name = self.ast_parse_based_baker.baker(code)
        if api_qualified_name is None:
            api_qualified_name = self.code_based_baker.baker(code)
        return api_qualified_name
