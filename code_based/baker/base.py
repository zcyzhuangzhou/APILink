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
from abc import abstractmethod
import re
import javalang
import javalang.tree as Tree
from nltk import word_tokenize
from sekg.graph.exporter.graph_data import GraphData
from sekg.util.code import CodeElementNameUtil
from discussion.api_recognition.code_based.baker.BakerGraphAccessor import BakerGraphAccessor


class BakerBaseClass:
    def __init__(self, graph, graph_client):
        self.graph_accessor = BakerGraphAccessor(graph_client)
        self.qualified_name_set = set()
        self.long_name_dic = {}
        self.short_name_dic = {}
        self.api_graph = None
        if isinstance(graph, str):
            self.init_from_graph_data(graph)
        elif isinstance(graph, GraphData):
            self.api_graph = graph
            self.init_api_table()
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

    def init_from_graph_data(self, graph_path):
        self.api_graph: GraphData = GraphData.load(graph_path)
        self.init_api_table()

    def init_api_table(self,):
        api_node_ids = self.api_graph.get_node_ids_by_label("class")
        api_node_ids.update(self.api_graph.get_node_ids_by_label("method"))
        api_node_ids.update(self.api_graph.get_node_ids_by_label("interface"))
        for node_id in api_node_ids:
            api_node = self.api_graph.get_node_info_dict(node_id)
            qualified_name = api_node["properties"]["qualified_name"]
            long_name, short_name, parameter_list = self.process_api(qualified_name)
            self.qualified_name_set.add(qualified_name)
            if long_name not in self.long_name_dic.keys():
                self.long_name_dic[long_name] = {qualified_name}
            else:
                self.long_name_dic[long_name].add(qualified_name)
            if short_name not in self.short_name_dic.keys():
                self.short_name_dic[short_name] = {qualified_name}
            else:
                self.short_name_dic[short_name].add(qualified_name)

    @abstractmethod
    def baker(self, code):
        return set()

    def extract_code_element(self, sent):
        elements = set()
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
            if index == len(words) - 1:
                break
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
                false_method.add(words[index + 1])
                if p2.match(words[index + 1]) is not None:
                    class_object_pair.setdefault(word, []).append(words[index + 1])
        # print("类和对象配对：", class_object_pair)
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

    def recognize_valid_code(self, code):
        """
        去除code中的注释
        :param code: 原始代码片段
        :return: 修改后的合法代码片段
        """
        self.pattern_line = "\/\/[^\n]*"
        self.pattern_block = "\/\*(\s|.)*?\*\/"
        self.pattern_code = re.compile("[a-zA-Z0-9_ ]")
        self.pattern_method = re.compile("\([^()]+\)")
        self.pattern_parameter = re.compile('([a-zA-Z0-9_ ]+)([^a-zA-Z0-9_ ])')
        try:
            code = re.sub(self.pattern_line, '', code, flags=re.I)
            # code = re.sub(self.pattern_block, '', code, flags=re.M)
            code = re.sub("\n[\s]*\n", '\n', code, flags=re.I)
        except Exception as e:
            print(str(e))
        code_lines = code.split('\n')
        # 去除code_lines中的空格和import语句
        code_lines = list(filter(lambda x: x != '' and not x.isspace() and not x.startswith('import'), code_lines))
        for code_line in code_lines:
            if code_line.__contains__('...'):
                return
            elif code_line.strip()[-1] not in ['{', '}', ')', ';'] and code_line.strip()[0] not in ['@']:
                return
            elif code_line.strip()[-1] in ['{', '}', ')', ';'] and not self.pattern_code.match(code_line) and not code_line.strip()[0] in ['{', '}', ')', ';']:
                return
        for index, code_line in enumerate(code_lines.copy()):
            if not code_line.startswith('if') and code_line.endswith(')'):
                code_lines[index] = code_lines[index] + ';'
            results = self.pattern_method.findall(code_line)
            if len(results) > 0:
                for i, result in enumerate(results.copy()):
                    parameters = result.lstrip('(').rstrip(')').split(',')
                    for j, parameter in enumerate(parameters.copy()):
                        if self.pattern_parameter.search(parameter) is not None:
                            parameters[j] = self.pattern_parameter.search(parameter).group(1)
                        else:
                            parameters[j] = parameter
                    results[i] = ','.join(parameters)
                    results[i] = '(' + results[i] + ')'
                    code_lines[index] = code_lines[index].replace(result, results[i])
        code = '\n'.join(code_lines)
        return code

    def recognize_code_block(self, code):
        code_blocks = []
        code_lines = code.split('\n')
        line_index = 0
        while line_index < len(code_lines):
            if code_lines[line_index].__contains__('class ' or 'interface '):
                start_index = line_index
                brackets = []
                if code_lines[line_index].__contains__('{' and '}'):
                    code_blocks.append(code_lines[line_index])
                    line_index = line_index + 1
                    continue
                if code_lines[line_index].__contains__('{'):
                    brackets.append("{")
                line_index = line_index + 1
                if line_index >= len(code_lines):
                    break
                code = ''
                while True:
                    if code_lines[line_index].__contains__('{'):
                        brackets.append('{')
                    if code_lines[line_index].__contains__('}'):
                        brackets.pop()
                    end_index = line_index + 1
                    line_index = line_index + 1
                    if len(brackets) <= 0:
                        break
                    if line_index >= len(code_lines):
                        break
                for code_index in range(start_index, end_index):
                    code = code + code_lines[code_index] + '\n'
                code_blocks.append(code)
            line_index = line_index + 1
        return code_blocks

    def recognize_method_signature(self, code):
        method_signature_patterns = [
            re.compile(
                r'(public |private |protected )(void |abstract |static |final |native |synchronized )?'
                r'[a-zA-Z0-9_ ]+(\([a-zA-Z0-9_, ]*\))')
        ]
        code_lines = code.split('\n')
        for code_line in code_lines:
            for index, pattern in enumerate(method_signature_patterns):
                search_rs = pattern.match(code_line)
                if search_rs is not None:
                    return True
        return False

    def code_completion(self, code):
        if self.recognize_method_signature(code):
            return "public class DummyClass{\n" + code + "\n }"
        else:
            return "public class DummyClass{\n" + " public void dummyMethod(){\n" + code + " }\n" + "}"

    def code_parser(self, code):
        class_object_pair = {}
        class_method_dic = {}
        class_extends_implements = ''
        try:
            tree = javalang.parse.parse(code)
            class_trees = tree.types
            for class_tree in class_trees:
                for path, node in class_tree:
                    if isinstance(node, Tree.ClassDeclaration):
                        if node.extends is not None:
                            class_extends_implements = node.extends.name
                            class_method_dic[class_extends_implements] = []
                        elif node.implements is not None:
                            class_extends_implements = node.implements.name
                            class_method_dic[class_extends_implements] = []
                    elif isinstance(node, Tree.MethodDeclaration):
                        if node.annotations is not None:
                            for annotation in node.annotations:
                                if annotation.name == 'Override':
                                    class_method_dic.setdefault(class_extends_implements, []).append(node.name)
                    elif isinstance(node, Tree.SuperMethodInvocation):
                        class_method_dic.setdefault(class_extends_implements, []).append(node.member)
                    elif isinstance(node, Tree.ClassCreator):
                        class_method_dic[node.type.name] = []
                    elif isinstance(node, Tree.LocalVariableDeclaration):
                        for declarator in node.declarators:
                            class_object_pair.setdefault(node.type.name, []).append(declarator.name)
                        class_method_dic[node.type.name] = []
                    elif isinstance(node, Tree.ReferenceType):
                        if node.name not in class_method_dic.keys():
                            class_method_dic[node.name] = []
                    elif isinstance(node, Tree.MethodInvocation) and node.qualifier is not None:
                        if len(class_object_pair) > 0:
                            for class_object_pair_value in class_object_pair.values():
                                if node.qualifier in class_object_pair_value:
                                    class_method_dic.setdefault(list(class_object_pair.keys())[
                                                                         list(class_object_pair.values()).index(
                                                                             class_object_pair_value)], []).append(
                                        node.member)
                                else:
                                    class_method_dic.setdefault(node.qualifier, []).append(node.member)
                        else:
                            class_method_dic.setdefault(node.qualifier, []).append(node.member)
                        if node.selectors is not None:
                            for selector in node.selectors:
                                class_method_dic.setdefault(node.qualifier + '.' + node.member, []).append(
                                    selector.member)
            # print("类和对象配对:", class_object_pair)
            # print("javalang解析:", class_method_dic)
        except Exception as e:
            print('the code can not be parsed')
            return
        return class_object_pair, class_method_dic

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
        # print("locate信息: ", locate_class_method_dic)
        return locate_class_method_dic

    def neo4j_based_linker(self, locate_class_method_dic, class_object_pair):
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
                if self.graph_accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=class_api):
                    api_qualified_name[locate_class_api] = class_api
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = class_api + '.' + locate_method_api.split('[')[0]
                    continue
                candidate_classes = set()
                short_name_node = self.graph_accessor.find_node(primary_label="entity", primary_property="short_name",
                                                                primary_property_value=class_api)
                if short_name_node is not None:
                    candidate_classes.add(short_name_node["qualified_name"])
                long_name_node = self.graph_accessor.find_node(primary_label="entity", primary_property="long_name",
                                                               primary_property_value=class_api)
                if long_name_node is not None:
                    candidate_classes.add(long_name_node["qualified_name"])
                tmp_api_qualified_name = dict()
                for candidate_class in candidate_classes:
                    qualified_name_node = self.graph_accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=candidate_class)
                    if qualified_name_node is not None:
                        graph_id = qualified_name_node.identity
                        in_relations_tuples = self.graph_accessor.get_all_in_relations(graph_id)
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
                        short_name_node = self.graph_accessor.find_node(primary_label="entity",
                                                                        primary_property="short_name",
                                                                        primary_property_value=return_value_type_name)
                        if short_name_node is not None:
                            qualified_names = short_name_node["qualified_name"]
                        long_name_node = self.graph_accessor.find_node(primary_label="entity",
                                                                       primary_property="long_name",
                                                                       primary_property_value=return_value_type_name)
                        if long_name_node is not None:
                            qualified_names = long_name_node["qualified_name"]
                        first_flag = False
                        for qualified_name in qualified_names:
                            api_node = self.graph_accessor.find_node(primary_label="entity", primary_property="qualified_name", primary_property_value=qualified_name)
                            if api_node is not None:
                                graph_id = api_node.identity
                                out_relations_tuples = self.graph_accessor.get_all_out_relations(graph_id)
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
        # print("baker链接: ", api_qualified_name)
        return api_qualified_name

    def graph_based_linker(self, locate_class_method_dic, class_object_pair):
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
                if class_api in self.qualified_name_set:
                    api_qualified_name[locate_class_api] = class_api
                    for index, locate_method_api in enumerate(locate_method_apis):
                        api_qualified_name[locate_method_api] = class_api + '.' + locate_method_api.split('[')[0]
                    continue
                candidate_classes = set()
                if class_api in self.short_name_dic:
                    candidate_classes.update(self.short_name_dic[class_api])
                if class_api in self.long_name_dic:
                    candidate_classes.update(self.long_name_dic[class_api])
                tmp_api_qualified_name = dict()
                for candidate_class in candidate_classes:
                    candidate_class_node = self.api_graph.find_one_node_by_property("qualified_name", candidate_class)
                    if candidate_class_node is None:
                        continue
                    node_id = candidate_class_node['id']
                    in_relations_tuples = self.api_graph.get_all_in_relations(node_id)
                    all_methods = []
                    for in_relations_tuple in in_relations_tuples:
                        if in_relations_tuple[1] == 'belong to':
                            all_methods.append(
                                self.api_graph.get_node_info_dict(in_relations_tuple[0])["properties"]["qualified_name"])
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
                        if return_value_type_name in self.short_name_dic:
                            qualified_names = self.short_name_dic[return_value_type_name]
                        if return_value_type_name in self.long_name_dic:
                            qualified_names = self.long_name_dic[return_value_type_name]
                        first_flag = False
                        for qualified_name in qualified_names:
                            api_node = self.api_graph.find_one_node_by_property("qualified_name", qualified_name)
                            node_id = api_node['id']
                            out_relations_tuples = self.api_graph.get_all_out_relations(node_id)
                            for out_relations_tuple in out_relations_tuples:
                                if out_relations_tuple[1] == 'return value type' or out_relations_tuple[1] == 'has return value':
                                    first_flag = True
                                    return_value_type = self.api_graph.get_node_info_dict(out_relations_tuple[2])["properties"]["qualified_name"]
                                    for method_name in locate_class_method_dic[locate_class_api]:
                                        api_qualified_name[method_name] = str(return_value_type) + '.' + str(method_name.split('[')[0])
                                    break
                            if first_flag:
                                break
                        break
        # print("baker链接: ", api_qualified_name)
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
