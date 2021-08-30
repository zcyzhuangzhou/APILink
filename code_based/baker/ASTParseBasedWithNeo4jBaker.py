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
from discussion.api_recognition.code_based.baker.base import BakerBaseClass


class ASTParseBasedWithNeo4jBaker(BakerBaseClass):
    """
    baker based on AST parse with neo4j
    """
    def __init__(self, graph_client, graph=None):
        super().__init__(graph_client=graph_client, graph=graph)

    def baker(self, code):
        api_qualified_name = {}
        valid_code = self.recognize_valid_code(code)
        if valid_code is not None:
            code_blocks = self.recognize_code_block(valid_code)
            if len(code_blocks) > 0:
                for code_block in code_blocks:
                    if self.code_parser(code_block) is not None:
                        class_object_pair, class_method_dic = self.code_parser(code_block)
                        locate_class_method_dic = self.locate_api(code, class_method_dic)
                        api_qualified_name = self.neo4j_based_linker(locate_class_method_dic, class_object_pair)
                    else:
                        return
            else:
                if self.code_parser(self.code_completion(valid_code)) is not None:
                    class_object_pair, class_method_dic = self.code_parser(self.code_completion(valid_code))
                    locate_class_method_dic = self.locate_api(code, class_method_dic)
                    api_qualified_name = self.neo4j_based_linker(locate_class_method_dic, class_object_pair)
                else:
                    return
        else:
            print("invalid code")
            return
        return api_qualified_name
