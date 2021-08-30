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
from discussion.api_recognition.code_based.baker.ASTParseBasedWithNeo4jBaker import ASTParseBasedWithNeo4jBaker
from discussion.api_recognition.code_based.baker.CodeBasedWithNeo4jBaker import CodeBasedWithNeo4jBaker
from discussion.api_recognition.code_based.baker.base import BakerBaseClass


class ASTParseCodeBasedWithNeo4jBaker(BakerBaseClass):
    """
    baker based on AST parse + code recognize with neo4j
    """
    def __init__(self, graph_client, graph=None):
        super().__init__(graph_client=graph_client, graph=graph)
        self.code_based_baker = CodeBasedWithNeo4jBaker(graph_client=graph_client)
        self.ast_parse_based_baker = ASTParseBasedWithNeo4jBaker(graph_client=graph_client)

    def baker(self, code):
        api_qualified_name = self.ast_parse_based_baker.baker(code)
        if api_qualified_name is None:
            api_qualified_name = self.code_based_baker.baker(code)
        return api_qualified_name
