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


class CodeBasedWithNeo4jBaker(BakerBaseClass):
    """
    baker based on code recognize with neo4j
    """
    def __init__(self, graph_client, graph=None):
        super().__init__(graph=graph, graph_client=graph_client)

    def baker(self, code):
        class_recognitions, false_classes = self.extract_class_from_code(code)
        method_recognitions, class_object_pair = self.extract_method_from_code(code)
        # print("类：", class_recognitions)
        # print("方法：", method_recognitions)
        class_method_dic = {}
        for class_recognition in class_recognitions:
            class_method_dic[class_recognition] = []
        for method_recognition in method_recognitions:
            class_method_dic.setdefault(method_recognition.split('.')[0], []).append(method_recognition.split('.')[-1])
        # print("类及其方法：", class_method_dic)
        locate_class_method_dic = self.locate_api(code, class_method_dic)
        api_qualified_name = self.neo4j_based_linker(locate_class_method_dic, class_object_pair)
        return api_qualified_name
