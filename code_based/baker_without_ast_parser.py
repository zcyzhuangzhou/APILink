#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/12/8
------------------------------------------
@Modify: 2019/12/8
------------------------------------------
@Description: 
"""
import re
from nltk import WordPunctTokenizer, word_tokenize
from sekg.graph.accessor import GraphAccessor
from sekg.util.code import CodeElementNameUtil
from definitions import GRAPH_FACTORY


class BakerBasedWithoutParserSOPostAPILinker:
    """
    baker based on neo4j without ast parser
    """
    def __init__(self):
        self.graph_client = GRAPH_FACTORY.create_py2neo_graph_by_server_name(server_name="87Neo4jMavenApi")
        self.accessor = GraphAccessor(self.graph_client)
        self.CODE_NAME_UTIL = CodeElementNameUtil()
        self.code_patterns = [
            re.compile(r'^(?P<ELE>[a-zA-Z0-9_]*[a-z0-9][A-Z][a-z]+[a-zA-Z0-9_]*)(<.*>)?$'),
            re.compile(r'^(?P<ELE>[a-zA-Z0-9_\.<>]+)\)[a-zA-Z0-9_\,.<>)]*?$'),
            re.compile(r'^(?P<ELE>[a-zA-Z]{2,}(\.[a-zA-Z0-9_]+)+)(<.*>)?$'),
            re.compile(r'^(?P<ELE>((([a-zA-Z0-9_]+)(\.))+)([a-zA-Z0-9_]+))?$'),
            re.compile(r'^(?P<ELE>[a-zA-Z0-9_]+(\([a-zA-Z0-9_]*\))?\.)+[a-zA-Z0-9_]+(\([a-zA-Z0-9_]*\))$')
        ]
        self.data_type = {'boolean', 'byte', 'char', 'short', 'int', 'long', 'float', 'double', 'Boolean', 'Byte',
                          'Character', 'Short', 'Integer', 'Long', 'Float', 'Double', 'void', 'enum'}

    def baker(self, code):
        class_recognitions, false_classes = self.extract_class_from_code(code)
        method_recognitions, class_object_pair = self.extract_method_from_code(code)
        print("类：", class_recognitions)
        print("方法：", method_recognitions)
        class_method_dic = {}
        for class_recognition in class_recognitions:
            class_method_dic[class_recognition] = []
        for method_recognition in method_recognitions:
            class_method_dic.setdefault(method_recognition.split('.')[0], []).append(method_recognition.split('.')[-1])
        print("类及其方法：", class_method_dic)
        locate_class_method_dic = self.locate_api(code, class_method_dic)
        api_qualified_name = self.linker(locate_class_method_dic, class_object_pair)
        return api_qualified_name

    def extract_code_element(self, sent):
        elements = set()
        # raw_words = WordPunctTokenizer().tokenize(sent)
        raw_words = word_tokenize(sent)
        words = []
        for raw_word in raw_words:
            words.append(raw_word.strip())
        # 去除words中的空格
        words = list(filter(lambda x: x != '', words))
        for word in words:
            flag = False
            for index, pattern in enumerate(self.code_patterns):
                search_rs = pattern.search(word)
                if search_rs is not None and search_rs.group("ELE"):
                    elements.add(search_rs.group("ELE"))
                    flag = True
                # 若是不符合上述任何一种pattern,则考虑当前分词中是否存在驼峰式
                elif index == len(self.code_patterns) - 1 and not flag:
                    p = re.compile(r'(([a-z_]+([A-Z])[a-z_]+)+)|(([A-Z_]([a-z_]+))+)')
                    search_rs = p.match(word)
                    if search_rs is not None:
                        elements.add(search_rs.group(0))
        return elements, words

    def extract_class_from_code(self, sent):
        candidate_classes = set()
        code_elements, words = self.extract_code_element(sent)
        pattern_qualified_name = re.compile(r'(java.)|(javax.)|(org.)')
        pattern_simple_name = re.compile(r'([A-Z])')
        for code_element in code_elements:
            match_qualified_name = pattern_qualified_name.match(code_element)
            match_simple_name = pattern_simple_name.match(code_element)
            if match_qualified_name is not None:
                candidate_classes.add(code_element)
            if match_simple_name is not None:
                candidate_classes.add(code_element.split('.')[0])
        false_classes = set()
        for index, word in enumerate(words):
            if word == "class" or word == "@":
                false_classes.add(words[index + 1])
        for candidate_class in candidate_classes.copy():
            for false_class in false_classes:
                if candidate_class.startswith(false_class):
                    if candidate_class not in candidate_classes:
                        continue
                    candidate_classes.remove(candidate_class)
        return candidate_classes, false_classes

    def extract_method_from_code(self, sent):
        candidate_methods = set()
        code_methods = set()
        methods = set()
        class_object_pair = {}
        code_elements, words = self.extract_code_element(sent)
        code_classes, false_classes = self.extract_class_from_code(sent)
        p = re.compile(r'([a-z]+[a-zA-Z0-9_]*)')
        for code_element in code_elements:
            match_rs = p.match(code_element)
            if match_rs is not None:
                candidate_methods.add(code_element)
            for code_class in code_classes:
                if code_element.startswith(code_class + '.'):
                    candidate_methods.add(code_element)
        for code_class in code_classes.copy():
            code_classes.add(self.CODE_NAME_UTIL.simplify(code_class))
        false_method = set()
        false_mothod_from_false_classes = set()
        p2 = re.compile(r'([a-zA-Z0-9_]+)')
        for index, word in enumerate(words[:-1]):
            if word in false_classes:
                false_mothod_from_false_classes.add(words[index + 1])
                false_method.add(words[index + 1])
            elif word in code_classes | self.data_type:
                # if index == len(words) - 1:
                #     continue
                false_method.add(words[index + 1])
                if p2.match(words[index + 1]) is not None:
                    class_object_pair.setdefault(word, []).append(words[index + 1])
        print("类和对象配对：", class_object_pair)
        for candidate_method in candidate_methods - false_method - code_classes:
            if candidate_method.split('.')[0] not in false_mothod_from_false_classes and \
                    candidate_method.split('.')[-1][0].islower() and candidate_method.__contains__('.'):
                code_methods.add(candidate_method)
        for code_method in code_methods.copy():
            class_name = code_method.split('.')[0]
            if class_name in class_object_pair.keys():
                methods.add(code_method)
            else:
                for class_object_pair_value in class_object_pair.values():
                    if class_name in class_object_pair_value:
                        methods.add(str(list(class_object_pair.keys())[
                            list(class_object_pair.values()).index(
                                class_object_pair_value)]) + '.' + str(code_method.split('.', 1)[1]))
        return methods, class_object_pair

    def locate_api(self, code, class_method_dic):
        locate_class_method_dic = {}
        for key in class_method_dic.keys():
            tmp_method = []
            new_key = key + str([m.span() for m in re.finditer(key, code)])
            locate_class_method_dic.setdefault(new_key, [])
            for value in class_method_dic[key]:
                if value not in tmp_method:
                    indexes = [m.span() for m in re.finditer(value, code)]
                    if len(indexes) > 1:
                        tmp_method.append(value)
                        for index in indexes:
                            new_value = str(value) + '[' + str(index) + ']'
                            locate_class_method_dic.setdefault(new_key, []).append(new_value)
                    else:
                        locate_class_method_dic.setdefault(new_key, []).append(str(value) + str(indexes))
        print("locate信息: ", locate_class_method_dic)
        return locate_class_method_dic

    def linker(self, locate_class_method_dic, class_object_pair):
        api_qualified_name = {}
        locate_class_apis = locate_class_method_dic.keys()
        for locate_class_api in locate_class_apis:
            class_api = locate_class_api.split('[')[0]
            if not class_api.__contains__('.'):
                locate_method_apis = locate_class_method_dic[locate_class_api]
                simple_methods = []
                for locate_method_api in locate_method_apis:
                    method_api = locate_method_api.split('[')[0]
                    simple_methods.append(self.CODE_NAME_UTIL.simplify(method_api))
                # qualified name完全匹配--严格匹配
                if self.accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=class_api):
                    api_qualified_name[locate_class_api] = class_api
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = class_api + '.' + locate_method_api.split('[')[0]
                    continue
                candidate_classes = set()
                short_name_node = self.accessor.find_node(primary_label="entity", primary_property="short_name",
                                                          primary_property_value=class_api)
                if short_name_node is not None:
                    candidate_classes.add(short_name_node["qualified_name"])
                long_name_node = self.accessor.find_node(primary_label="entity", primary_property="long_name",
                                                         primary_property_value=class_api)
                if long_name_node is not None:
                    candidate_classes.add(long_name_node["qualified_name"])
                tmp_api_qualified_name = dict()
                for candidate_class in candidate_classes:
                    qualified_name_node = self.accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=candidate_class)
                    if qualified_name_node is not None:
                        graph_id = qualified_name_node.identity
                        in_relations_tuples = self.get_all_in_relations(graph_id)
                        all_methods = []
                        for in_relations_tuple in in_relations_tuples:
                            if in_relations_tuple[1] == 'belong to':
                                all_methods.append(in_relations_tuple[2])
                        all_simple_methods = []
                        for all_method in all_methods:
                            all_simple_methods.append(self.CODE_NAME_UTIL.simplify(all_method))
                        if set(simple_methods) < set(all_simple_methods):
                            tmp_api_qualified_name.setdefault(candidate_class, [])
                            for simple_method in simple_methods:
                                tmp_api_qualified_name.setdefault(candidate_class, []).append(
                                    candidate_class + '.' + simple_method)
                if len(tmp_api_qualified_name) == 1:
                    class_qualified_name = list(tmp_api_qualified_name.keys())[0]
                    method_qualified_name = tmp_api_qualified_name[class_qualified_name]
                    api_qualified_name[locate_class_api] = class_qualified_name
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = method_qualified_name[index]
            else:
                object_name = class_api.split('.')[0]
                class_name = ''
                qualified_names = set()
                for key in class_object_pair.keys():
                    if object_name in class_object_pair[key]:
                        class_name = key
                for key in api_qualified_name.keys():
                    if key.__contains__(class_name):
                        return_value_type_name = api_qualified_name[key] + '.' + class_api.split('.')[1]
                        short_name_node = self.accessor.find_node(primary_label="entity", primary_property="short_name",
                                                                  primary_property_value=return_value_type_name)
                        if short_name_node is not None:
                            qualified_names = short_name_node["qualified_name"]
                        long_name_node = self.accessor.find_node(primary_label="entity", primary_property="long_name",
                                                                 primary_property_value=return_value_type_name)
                        if long_name_node is not None:
                            qualified_names = long_name_node["qualified_name"]
                        first_flag = False
                        for qualified_name in qualified_names:
                            api_node = self.accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=qualified_name)
                            if api_node is not None:
                                graph_id = api_node.identity
                                out_relations_tuples = self.get_all_out_relations(graph_id)
                                for out_relations_tuple in out_relations_tuples:
                                    if out_relations_tuple[1] == 'return value type' or out_relations_tuple[1] == 'has return value':
                                        first_flag = True
                                        return_value_type = out_relations_tuple[2]
                                        for method_name in locate_class_method_dic[locate_class_api]:
                                            api_qualified_name[method_name] = str(return_value_type) + '.' + str(method_name.split('[')[0])
                                        break
                                if first_flag:
                                    break
                        break
        print("baker链接: ", api_qualified_name)
        return api_qualified_name

    def process_api(self, api):
        api_split_parentheses = api.split("(")
        long_name = api_split_parentheses[0].strip()
        short_name = long_name.split(".")[-1].strip()
        parameter_list_for_api = []
        if "(" in api and ")" in api:
            parameter_list_for_api = api_split_parentheses[1].split(")")[0].strip().split(",")
        parameter_list_result = []
        for item in parameter_list_for_api:
            item = item.strip()
            if item:
                p = item.split(" ")[0]
                parameter_list_result.append(p)
        return long_name, short_name, parameter_list_result

    def get_all_in_relations(self, graph_id):
        # query = 'match(n:entity{_node_id:%d}) <-[r]- (m) return n.qualified_name, type(r), m.qualified_name' % node_id
        query = 'match(n:entity) <-[r]- (m) where id(n) = %d return n.qualified_name, type(r), m.qualified_name' % graph_id
        r = self.accessor.graph.run(query).to_ndarray()
        if r is None:
            print("no in relations")
            return None
        return r

    def get_all_out_relations(self, graph_id):
        # query = 'match(n:entity{_node_id:%d}) -[r]-> (m) return n.qualified_name, type(r), m.qualified_name' % node_id
        query = 'match(n:entity) -[r]-> (m) where id(n) = %d return n.qualified_name, type(r), m.qualified_name' % graph_id
        r = self.accessor.graph.run(query).to_ndarray()
        if r is None:
            print("no out relations")
            return None
        return r
